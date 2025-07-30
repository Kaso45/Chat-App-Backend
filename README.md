# Backend for Chat App
This is the backend for the chat app application that I working on with my teammate. Here is the main Git application:

https://github.com/ThanhfVux2102/F.E-Chat-Web

# Initialization
- Use the local environment:
```
Windows Powershell:
.venv/Scripts/Activate.ps1
```

- Get all the needed dependencies:
```
pip install -r requirements.txt
```

- Run in development mode:
```
fastapi dev main.py

or

uvicorn app.main:app --reload
```

- API docs:
```
localhost:8000/docs
```

# API Documentation
## Auth Endpoints
### Login
- Method: `POST`
- URL: {{BaseURL}}/api/auth/login
- Request body:
```
{
  "email": "user@example.com",
  "password": "string"
}
```
- Responses:

```
{
    "Login succesfully"
}
```

```
{
    "detail": "401: Wrong password"
}
```

```
{
    "detail": "User not found"
}
```

### Register
- Method: `POST`
- URL: {{BaseURL}}/api/auth/register
- Request body:
```
{
  "email": "user@example.com",
  "username": "string",
  "password": "string"
}
```
- Responses:

```
{
    "msg": "string",
    "user_id": "string"
}
```

```
{
    "detail": "User already exists"
}
```

### Forgot password
- Method: `POST`
- URL: {{BaseURL}}/api/auth/forgot-password
- Request body:
```
{
    "email": "user@example.com"
}
```
- Responses:

```
{
    "msg": "string",
}
```

```
{
    "detail": "User not found"
}
```

### Reset password
- Method: `POST`
- URL: {{BaseURL}}/api/auth/reset-password?token=...
- Request body:
```
{
    "new_password": "string",
    "confirm_password": "string"
}
```
- Responses:

```
{
    "msg": "string",
}
```

```
{
    "detail": "Invalid or expired token"
}
```

```
{
    "detail": "Password not match"
}
```

### Logout
- Method: `POST`
- URL: {{BaseURL}}/api/auth/logout
- Responses:

```
{
    "Successfully logged out",
}
```