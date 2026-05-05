import os, sys, traceback
os.environ['FLASK_ENV'] = 'development'

from app import create_app
app = create_app('development', {
    'TESTING': True,
    'WTF_CSRF_ENABLED': False,
    'PROPAGATE_EXCEPTIONS': True,
})

with app.test_client() as c:
    r0 = c.post('/auth/login', data={
        'username': 'Abdoulaye Diop',
        'password': 'admin123',
    })
    print('Login:', r0.status_code)

    try:
        r = c.get('/recettes-historiques/')
        print('STATUS:', r.status_code)
        if r.status_code != 200:
            print(r.data.decode('utf-8', errors='replace')[-3000:])
        else:
            print('OK - longueur:', len(r.data))
    except Exception:
        traceback.print_exc()
