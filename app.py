# Flask Hello World API route on port
from flask import Flask, request, jsonify
from pdfminer.high_level import extract_text, extract_text_to_fp
from pdfminer.layout import LAParams
from io import BytesIO, StringIO
import time
from flask import Flask, request, jsonify
import sagemaker
from sagemaker.huggingface import get_huggingface_llm_image_uri, HuggingFaceModel
import json
import boto3
import os
from dotenv import load_dotenv

app = Flask(__name__)

# Global variable to store the deployed model reference and endpoint name
llm = None
endpoint_name = "simplereads-model" # consistent naming convention

def check_endpoint_status():
    client = boto3.client('sagemaker')
    try:
        response = client.describe_endpoint(EndpointName=endpoint_name)
        return response['EndpointStatus']
    except:
        return None



def load_env_variables():
    load_dotenv()
    return {
        'aws_default_region': os.getenv("AWS_DEFAULT_REGION"),
        'aws_access_key_id': os.getenv('AWS_ACCESS_KEY_ID'),
        'aws_secret_access_key': os.getenv('AWS_SECRET_ACCESS_KEY'),
        'sagemaker_role_arn': os.getenv("SAGEMAKER_ROLE_ARN")
    }

def create_boto_session(env_vars):
    return boto3.Session(
        aws_access_key_id=env_vars['aws_access_key_id'],
        aws_secret_access_key=env_vars['aws_secret_access_key'],
        region_name=env_vars['aws_default_region']
    )

def get_sagemaker_role_arn(env_vars):
    try:
        return env_vars['sagemaker_role_arn']
    except ValueError:
        iam = boto3.client('iam')
        return iam.get_role(RoleName='sagemaker_execution_role')['Role']['Arn']

def get_sagemaker_session(boto_session):
    sess = sagemaker.Session(boto_session=boto_session)
    sagemaker_session_bucket = sess.default_bucket()
    return sagemaker.Session(default_bucket=sagemaker_session_bucket)

def deploy_model(sess, role):
    # Configuration
    llm_image = get_huggingface_llm_image_uri("huggingface", version="0.9.3")
    s3_model_uri = os.getenv("S3_MODEL_URI")
    instance_type = "ml.g5.12xlarge"
    number_of_gpu = 4
    health_check_timeout = 300
    config = {
        'HF_MODEL_ID': "/opt/ml/model",
        'SM_NUM_GPUS': json.dumps(number_of_gpu),
        'MAX_INPUT_LENGTH': json.dumps(1024),
        'MAX_TOTAL_TOKENS': json.dumps(2048),
    }
    llm_model = HuggingFaceModel(
        role=role,
        image_uri=llm_image,
        model_data=s3_model_uri,
        env=config
    )

    # Check if endpoint with given name exists
    sagemaker_client = boto3.client('sagemaker')
    try:
        sagemaker_client.describe_endpoint(EndpointName=endpoint_name)
        print(f"Endpoint {endpoint_name} already exists. Not deploying a new one.")
        return None  # You can also return an instance of the existing model if needed.
    except sagemaker_client.exceptions.ClientError:
        pass  # Endpoint does not exist, proceed with deployment.

    return llm_model.deploy(
        initial_instance_count=1,
        instance_type=instance_type,
        container_startup_health_check_timeout=health_check_timeout,
        endpoint_name=endpoint_name  # Add this line to use a consistent endpoint name
    )



def construct_simplification_instruction(text):
    """
    Constructs a simplification instruction based on the provided text.
    """
    return f"Please syntactically simplify this sentence: {text}"

def get_simplified_text(text, model):
    """
    Sends a simplification request to the model and returns the simplified text.
    """
    instruction = construct_simplification_instruction(text)
    payload = {
        "inputs": instruction,
        "parameters": {
            "do_sample": True,
            "top_p": 0.9,
            "temperature": 0.8,
            "max_new_tokens": 1024,
            "repetition_penalty": 1.03,
            "stop": []
        }
    }

    # send request to endpoint
    serialized_payload = json.dumps(payload).encode('utf-8')
    model.content_type = "application/json"
    response = model.predict(serialized_payload)
    decoded_response = response.decode('utf-8')
    parsed_response = json.loads(decoded_response)

    print("response", parsed_response)
    output = parsed_response[0]['generated_text']
    # \n\n### Answer\nWe present QLORA remove everything before and including ### Answer
    output = output.split("### Answer\n")[1]
    return output

# # example function that does not inference
# def get_simplified_text(text, model):
#     return text


# @app.route("/start", methods=["POST"])
# def start():
#     # global llm
#     try:
#         message = "START"
#         # env_vars = load_env_variables()
#         # boto_session = create_boto_session(env_vars)
#         # role = get_sagemaker_role_arn(env_vars)
#         # sess = get_sagemaker_session(boto_session)
#         # llm = deploy_model(sess, role)
#         response = jsonify({"message": message})
#     except Exception as e:
#         response = jsonify({"message": f"Error: {str(e)}"})
#         response.status_code = 500  # Indicates a server error

#     response.headers.add("Access-Control-Allow-Origin", "*")
#     return response

def check_endpoint_status():
    """
    Check the status of the SageMaker endpoint.
    """
    # We assume you have your AWS credentials set up either as environment variables or in a configuration file.
    sagemaker_client = boto3.client('sagemaker')
    try:
        # Use the global endpoint name you've defined
        response = sagemaker_client.describe_endpoint(EndpointName=endpoint_name)
        return response['EndpointStatus']
    except sagemaker_client.exceptions.ClientError as e:
        if e.response['Error']['Code'] == 'ValidationException':
            # Endpoint doesn't exist
            return None
        else:
            # Raise the exception if it's another kind of error
            raise


@app.route("/start", methods=["POST"])
def start():
    global llm
    try:
        endpoint_status = check_endpoint_status()

        if endpoint_status == "InService":
            message = "Model is already running"
        elif endpoint_status in ["Creating", "Updating", "RollingBack"]:
            message = "Model is starting up. Please wait."
        elif endpoint_status is None:  # The endpoint does not exist, so it's safe to deploy a new one.
            env_vars = load_env_variables()
            boto_session = create_boto_session(env_vars)
            role = get_sagemaker_role_arn(env_vars)
            sess = get_sagemaker_session(boto_session)
            llm = deploy_model(sess, role)
            message = "START"
        else:
            # Catch any other unexpected statuses
            message = f"Model has status '{endpoint_status}'. Not deploying a new model."

        response = jsonify({"message": message})
        print(message)
    except Exception as e:
        print(e)
        response = jsonify({"message": f"Error: {str(e)}"})
        response.status_code = 500

    response.headers.add("Access-Control-Allow-Origin", "*")
    return response



# @app.route("/stop", methods=["POST"])
# def stop():
#     # global llm
#     message = "STOP"
#     # if llm:
#     #     llm.delete_model()
#     #     llm.delete_endpoint()
#     #     print("Model and endpoint deleted successfully")
#     response = jsonify({"message": message})
#     response.headers.add("Access-Control-Allow-Origin", "*")
#     return response


@app.route("/stop", methods=["POST"])
def stop():
    global llm
    try:
        endpoint_status = check_endpoint_status()
        if endpoint_status == "InService":
            llm.delete_model()
            llm.delete_endpoint()
            print("Model and endpoint deleted successfully")
            message = "STOP"
        else:
            message = "Model is not running"
        
        response = jsonify({"message": message})
    except Exception as e:
        response = jsonify({"message": f"Error: {str(e)}"})
        response.status_code = 500

    response.headers.add("Access-Control-Allow-Origin", "*")
    return response


# @app.route("/simplify_text", methods=["POST"])
# def simplify():
#     data = request.json
#     text = data.get('text')
#     print(text)

#     # # Get the simplified text from the model
#     # simplified_text = get_simplified_text(text1, llm)

#     # response = jsonify({"message": simplified_text})
#     response = jsonify({"message": text})
#     response.headers.add("Access-Control-Allow-Origin", "*")
#     response.headers.add("Access-Control-Allow-Methods", "GET, POST")
#     return response


@app.route("/simplify_text", methods=["POST"])
def simplify():
    global llm
    data = request.json
    text = data.get('text')
    print("initial", text)
    
    # Check if the model reference is None
    if not llm:
        llm = sagemaker.predictor.RealTimePredictor(endpoint_name=endpoint_name)

    # Get the simplified text from the model
    simplified_text = get_simplified_text(text, llm)
    print("simplified", simplified_text)

    response = jsonify({"message": simplified_text})
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Methods", "GET, POST")
    return response



@app.route("/parsePDF", methods=["POST"])
def parsePDF():
    try:
        file = request.files["File"].stream.read()
        b = BytesIO(file)
        output_string = StringIO("A")
        extract_text_to_fp(b, output_string, laparams=LAParams(), output_type='text', codec=None)
        output_string.seek(0)
        response = jsonify({"message": output_string.read()})

        # Headers to give CORS clearance
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Methods", "GET, POST")
        return response

    except Exception as e:
        print("Error occurred:", e)
        # Return an error response
        response = jsonify({"error": str(e)})
        response.status_code = 500
        return response


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)

