
from app import app
from python import global_variables as gl

if __name__ == '__main__':
    if gl.DEBUG_MODE:
        app.run(host='0.0.0.0', port=5000, debug=True)
    else:
        app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)



