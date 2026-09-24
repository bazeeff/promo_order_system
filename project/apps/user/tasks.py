# from fcm_django.models import FCMDevice
#
# from apps import app
#
#
# @app.task
# def send_fcm_message_task(users_id_list, **kwargs):
#     devices = FCMDevice.objects.filter(user__id__in=users_id_list)
#     devices.send_message(**kwargs)
