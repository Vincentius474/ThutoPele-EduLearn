category_icons = {
    'Programming': '💻',
    'Robotics': '🤖',
    'Artificial Intelligence': '🧠',
    'Machine Learning': '📊',
    'Networking': '🌐',
    'Cyber Security': '🛡️'
}

category_colors = {
    'Programming': 'primary',
    'Robotics': 'success',
    'Artificial Intelligence': 'info',
    'Machine Learning': 'warning',
    'Networking': 'secondary',
    'Cyber Security': 'danger'
}

def get_category_icon(category):
    return category_icons.get(category, '📚')

def get_category_color(category):
    return category_colors.get(category, 'primary')