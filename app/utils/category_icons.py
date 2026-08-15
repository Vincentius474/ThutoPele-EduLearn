category_icons = {
    'Programming': '💻',
    'Robotics': '🤖',
    'Artificial Intelligence': '🧠',
    'Machine Learning': '📊',
    'Networking': ' 🌐',
    'Cyber Security': '🛡️',
    'Systems': '⚙️',
    'Data Science': '📈',
    'Cloud Computing': '☁️',
    'Blockchain': '⛓️',
    'General': '📚',
    'Other': '🔧'
}

category_colors = {
    'Programming': 'primary',
    'Robotics': 'success',
    'Artificial Intelligence': 'info',
    'Machine Learning': 'warning',
    'Networking': 'secondary',
    'Cyber Security': 'danger',
    'Systems': 'secondary',
    'Data Science': 'warning',
    'Cloud Computing': 'info',
    'Blockchain': 'dark',
    'General': 'primary',
    'Other': 'light'
}

category_names = list(category_icons.keys())


def get_category_icon(category):
    return category_icons.get(category, ' ')


def get_category_color(category):
    return category_colors.get(category, 'primary')