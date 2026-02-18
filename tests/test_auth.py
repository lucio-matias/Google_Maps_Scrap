
import pytest
from unittest.mock import patch
from server import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture
def mock_users_store():
    # This dictionary acts as our "database"
    store = {}
    
    # Mock load_users and save_users in server.py
    with patch("server.load_users") as mock_load, \
         patch("server.save_users") as mock_save:
        
        # load_users returns a copy of the store
        mock_load.side_effect = lambda: store.copy()
        
        # save_users updates the store
        def save(new_users):
            store.clear()
            store.update(new_users)
            
        mock_save.side_effect = save
        
        yield store

def test_register_success(client, mock_users_store):
    response = client.post('/api/register', json={
        'name': 'Test User',
        'email': 'test@example.com',
        'password': 'StrongPassword123!'
    })
    assert response.status_code == 201
    assert 'token' in response.json
    assert response.json['username'] == 'Test User'
    
    # Check store structure
    assert 'test@example.com' in mock_users_store
    user_entry = mock_users_store['test@example.com']
    assert user_entry['name'] == 'Test User'
    assert 'hash' in user_entry

def test_register_missing_fields(client, mock_users_store):
    response = client.post('/api/register', json={
        'name': 'Test User',
        'password': 'StrongPassword123!'
        # Missing email
    })
    assert response.status_code == 400
    assert 'error' in response.json

def test_register_invalid_email(client, mock_users_store):
    response = client.post('/api/register', json={
        'name': 'Test User',
        'email': 'invalid-email',
        'password': 'StrongPassword123!'
    })
    assert response.status_code == 400
    assert 'E-mail inválido' in response.json['error']

def test_register_weak_password_short(client, mock_users_store):
    response = client.post('/api/register', json={
        'name': 'Test User',
        'email': 'test@example.com',
        'password': 'Short1!'
    })
    assert response.status_code == 400
    assert 'pelo menos 8 caracteres' in response.json['error']

def test_register_weak_password_no_upper(client, mock_users_store):
    response = client.post('/api/register', json={
        'name': 'Test User',
        'email': 'test@example.com',
        'password': 'weakpassword123!'
    })
    assert response.status_code == 400
    assert 'letra maiúscula' in response.json['error']

def test_register_weak_password_no_number(client, mock_users_store):
    response = client.post('/api/register', json={
        'name': 'Test User',
        'email': 'test@example.com',
        'password': 'Weakpassword!'
    })
    assert response.status_code == 400
    assert 'pelo menos um número' in response.json['error']

def test_register_existing_user(client, mock_users_store):
    # Pre-populate store
    mock_users_store['test@example.com'] = {'name': 'Existing', 'hash': 'hash'}
    
    # Try to register again
    response = client.post('/api/register', json={
        'name': 'New Name',
        'email': 'test@example.com',
        'password': 'StrongPassword123!'
    })
    assert response.status_code == 409
    assert 'error' in response.json

def test_login_success(client, mock_users_store):
    # Register first (hashing needs to happen)
    client.post('/api/register', json={
        'name': 'Login User',
        'email': 'login@example.com',
        'password': 'StrongPassword123!'
    })
    
    # Login
    response = client.post('/api/login', json={
        'email': 'login@example.com',
        'password': 'StrongPassword123!'
    })
    assert response.status_code == 200
    assert 'token' in response.json
    assert response.json['username'] == 'Login User'

def test_login_invalid_credentials(client, mock_users_store):
    # Register first
    client.post('/api/register', json={
        'name': 'Login User',
        'email': 'login@example.com',
        'password': 'StrongPassword123!'
    })
    
    # Login with wrong password
    response = client.post('/api/login', json={
        'email': 'login@example.com',
        'password': 'WrongPassword123!'
    })
    assert response.status_code == 401
    assert 'error' in response.json

def test_protected_route_valid_token(client, mock_users_store):
    # Register to get token
    reg_response = client.post('/api/register', json={
        'name': 'Token User',
        'email': 'token@example.com',
        'password': 'StrongPassword123!'
    })
    token = reg_response.json['token']
    
    # Mock threading to avoid starting actual threads
    with patch('threading.Thread'): 
        response = client.post('/api/search', 
            json={'termo': 'test', 'cidade': 'city'},
            headers={'Authorization': f'Bearer {token}'}
        )
        assert response.status_code == 200
        assert 'job_id' in response.json
