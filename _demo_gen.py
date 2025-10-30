import inspect
from app.generator import generate_answer, healthcheck
import app.generator as g

print('health:', healthcheck())
print('generator file:', inspect.getsourcefile(g.generate_answer))
print('--- demo ---')
print(generate_answer('اصول مذاکره برد-برد چیست؟', context=[
    'مذاکره یعنی درک طرف مقابل، نیازها و ترس‌هایش. تمرکز بر منافع، نه مواضع.',
    'برد-برد یعنی راه‌حلی که هر دو طرف احساس برد داشته باشند.'
]))
