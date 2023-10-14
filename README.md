SimpleReads-API Documentation
============================

Before starting any operation, if accessing remotely, SSH into the Linux server.

Clone the Repository
--------------------
Clone the repository:
```
git clone https://github.com/simple-reads/SimpleReads-API.git
```
Navigate to the 'SimpleReads-API' Directory
------------------------------------------
Change directory:
```
cd SimpleReads-API
```

Accessing the 'api_session' Screen Session
------------------------------------------
This section provides a guide on managing and accessing the 'api_session' screen session where the Flask application is running.

Starting the Screen Session
```
screen -S api_session
```
Inside the 'screen' session, navigate to the directory and run the Flask application:
```
python3 app.py
```

Detaching from the Screen Session
Press 'Ctrl + A' followed by 'D' to detach from the 'api_session'. The Flask application will continue running in the background.

Reattaching to the Screen Session
```
screen -r api_session
```

Deleting the Screen Session
To delete the 'api_session' screen session:
```
screen -XS api_session quit
```

Connecting to the Virtual Environment
-------------------------------------
Navigate to the 'SimpleReads-API' directory:
```
cd SimpleReads-API
```
Activate the virtual environment:
```
source venv/bin/activate
```

Hosting the Flask Application
-----------------------------
Navigate to the 'SimpleReads-API' directory:
```
cd SimpleReads-API
```
Start or reattach to the 'api_session' screen session:
```
screen -S api_session
```
Activate the virtual environment:
```
source venv/bin/activate
```
Install the required packages:
```
pip install -r requirements.txt
```
Inside the 'screen' session, navigate to the directory and run the Flask application:
```
python app.py
```
Detach from the screen session using 'Ctrl + A + D'.

API Endpoints
-------------
This section details the various endpoints available in the SimpleReads-API.

**Start the Server**:
Endpoint: /start
Method: POST

**Stop the Server**:
Endpoint: /stop
Method: POST

**Simplify Text**:
Endpoint: /simplify_text
Method: POST

**Parse PDF**:
Endpoint: /parsePDF
Method: POST
