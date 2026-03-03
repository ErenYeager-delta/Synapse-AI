web: python manage.py migrate --noinput && python reconstruct_shadow.py && daphne -b 0.0.0.0 -p $PORT synapse_project.asgi:application
