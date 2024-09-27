from app.main import bp


@bp.route('/')
def index():
    return 'Welcome to the Model Registry API!'