import streamlit as st
import json
import os
import hashlib
from datetime import datetime
import uuid
import re

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
USERS_FILE = os.path.join(DATA_DIR, 'users.json')
SESSIONS_FILE = os.path.join(DATA_DIR, 'sessions.json')
MESSAGES_FILE = os.path.join(DATA_DIR, 'messages.json')

class AuthService:
    def __init__(self):
        # Local JSON-based auth system initialization
        os.makedirs(DATA_DIR, exist_ok=True)
        self._init_files()
        
        self.try_restore_session()

        if "auth_token" in st.session_state:
            if not self.validate_session_token():
                pass

    def _init_files(self):
        if not os.path.exists(USERS_FILE):
            admin_pwd = self._hash_password("admin123")
            admin_user = {
                "id": str(uuid.uuid4()),
                "email": "admin",
                "name": "Admin",
                "password": admin_pwd,
                "created_at": datetime.now().isoformat()
            }
            self._write_json(USERS_FILE, [admin_user])
        if not os.path.exists(SESSIONS_FILE):
            self._write_json(SESSIONS_FILE, [])
        if not os.path.exists(MESSAGES_FILE):
            self._write_json(MESSAGES_FILE, [])

    def _read_json(self, filepath):
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _write_json(self, filepath, data):
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=4)

    def _hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    def try_restore_session(self):
        if "auth_token" in st.session_state:
            token = st.session_state.auth_token
            users = self._read_json(USERS_FILE)
            for user in users:
                if user["id"] == token:
                    st.session_state.user = {k: v for k, v in user.items() if k != "password"}
                    return

    def validate_email(self, email):
        pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
        if email == "admin": 
            return True
        return bool(re.match(pattern, email))

    def check_existing_user(self, email):
        users = self._read_json(USERS_FILE)
        return any(u["email"] == email for u in users)

    def sign_up(self, email, password, name):
        if self.check_existing_user(email):
            return False, "Email already registered"

        users = self._read_json(USERS_FILE)
        user_id = str(uuid.uuid4())
        new_user = {
            "id": user_id,
            "email": email,
            "name": name,
            "password": self._hash_password(password),
            "created_at": datetime.now().isoformat()
        }
        users.append(new_user)
        self._write_json(USERS_FILE, users)

        user_data = {k: v for k, v in new_user.items() if k != "password"}
        st.session_state.auth_token = user_id
        st.session_state.user = user_data

        return True, user_data

    def sign_in(self, email, password):
        users = self._read_json(USERS_FILE)
        hashed_pwd = self._hash_password(password)

        for user in users:
            if user["email"] == email and user["password"] == hashed_pwd:
                user_data = {k: v for k, v in user.items() if k != "password"}
                st.session_state.auth_token = user["id"]
                st.session_state.user = user_data
                return True, user_data

        return False, "Invalid credentials"

    def sign_out(self):
        try:
            from auth.session_manager import SessionManager
            SessionManager.clear_session_state()
            return True, None
        except Exception as e:
            return False, str(e)

    def get_user(self):
        return st.session_state.get("user")

    def create_session(self, user_id, title=None):
        try:
            current_time = datetime.now()
            default_title = f"{current_time.strftime('%d-%m-%Y')} | {current_time.strftime('%H:%M:%S')}"
            
            session_id = str(uuid.uuid4())
            session_data = {
                "id": session_id,
                "user_id": user_id,
                "title": title or default_title,
                "created_at": current_time.isoformat()
            }
            
            sessions = self._read_json(SESSIONS_FILE)
            sessions.append(session_data)
            self._write_json(SESSIONS_FILE, sessions)
            
            return True, session_data
        except Exception as e:
            return False, str(e)

    def get_user_sessions(self, user_id):
        try:
            sessions = self._read_json(SESSIONS_FILE)
            user_sessions = [s for s in sessions if s["user_id"] == user_id]
            user_sessions.sort(key=lambda x: x["created_at"], reverse=True)
            return True, user_sessions
        except Exception as e:
            st.error(f"Error fetching sessions: {str(e)}")
            return False, []

    def save_chat_message(self, session_id, content, role="user"):
        try:
            message_data = {
                "id": str(uuid.uuid4()),
                "session_id": session_id,
                "content": content,
                "role": role,
                "created_at": datetime.now().isoformat()
            }
            messages = self._read_json(MESSAGES_FILE)
            messages.append(message_data)
            self._write_json(MESSAGES_FILE, messages)
            return True, message_data
        except Exception as e:
            return False, str(e)

    def get_session_messages(self, session_id):
        try:
            messages = self._read_json(MESSAGES_FILE)
            session_messages = [m for m in messages if m["session_id"] == session_id]
            session_messages.sort(key=lambda x: x["created_at"])
            return True, session_messages
        except Exception as e:
            return False, str(e)

    def delete_session(self, session_id):
        try:
            sessions = self._read_json(SESSIONS_FILE)
            sessions = [s for s in sessions if s["id"] != session_id]
            self._write_json(SESSIONS_FILE, sessions)
            
            messages = self._read_json(MESSAGES_FILE)
            messages = [m for m in messages if m["session_id"] != session_id]
            self._write_json(MESSAGES_FILE, messages)
            
            return True, None
        except Exception as e:
            st.error(f"Failed to delete session: {str(e)}")
            return False, str(e)

    def validate_session_token(self):
        if "auth_token" in st.session_state:
            token = st.session_state.auth_token
            users = self._read_json(USERS_FILE)
            for user in users:
                if user["id"] == token:
                    user_data = {k: v for k, v in user.items() if k != "password"}
                    return user_data
        return None

    def get_user_data(self, user_id):
        users = self._read_json(USERS_FILE)
        for user in users:
            if user["id"] == user_id:
                return {k: v for k, v in user.items() if k != "password"}
        return None
