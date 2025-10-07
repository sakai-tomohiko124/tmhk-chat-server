# routes.py
# Flaskルート定義を分割管理

def register_routes(app):
    from abcd import index, check_user, logout, check_login_status, terms, agree, virus_screen, apologize, pay, api_weather, api_train_delay, chat, debug_session, admin_dashboard, adjust_points, admin_chat, login, register, loading, keep_memo
    app.add_url_rule('/', 'index', index)
    app.add_url_rule('/check_user', 'check_user', check_user, methods=['POST'])
    app.add_url_rule('/logout', 'logout', logout)
    app.add_url_rule('/check_login_status', 'check_login_status', check_login_status)
    app.add_url_rule('/terms', 'terms', terms)
    app.add_url_rule('/agree', 'agree', agree, methods=['POST'])
    app.add_url_rule('/virus', 'virus_screen', virus_screen)
    app.add_url_rule('/apologize', 'apologize', apologize, methods=['POST'])
    app.add_url_rule('/pay', 'pay', pay)
    app.add_url_rule('/api/weather', 'api_weather', api_weather)
    app.add_url_rule('/api/train_delay', 'api_train_delay', api_train_delay)
    app.add_url_rule('/chat', 'chat', chat)
    app.add_url_rule('/debug_session', 'debug_session', debug_session)
    app.add_url_rule('/admin', 'admin_dashboard', admin_dashboard)
    app.add_url_rule('/admin/adjust_points', 'adjust_points', adjust_points, methods=['POST'])
    app.add_url_rule('/admin/chat/<int:user_id>', 'admin_chat', admin_chat)
    app.add_url_rule('/login', 'login', login, methods=['GET', 'POST'])
    app.add_url_rule('/register', 'register', register, methods=['GET', 'POST'])
    app.add_url_rule('/loading', 'loading', loading)
    app.add_url_rule('/admin/keep_memo', 'keep_memo', keep_memo, methods=['GET', 'POST'])
