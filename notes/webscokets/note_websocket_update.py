from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

channel_layer = get_channel_layer()


def send_note_update(user_id, data):
    print("SENDING WEBSOCKET EVENT:", data)
    async_to_sync(channel_layer.group_send)(
        f"user_{user_id}",
        {
            "type": "note_update",
            "data": data
        }
    )


def send_force_logout(user_id):
    print(f"Logging out user {user_id}")
    async_to_sync(channel_layer.group_send)(
        f"user_{user_id}",
        {
            "type": "force_logout",
        }
    )


def send_test_update(test: str, data):

    async_to_sync(channel_layer.group_send)(
        f"testing_{test}",
        {
            "type": "note_update",
            "data": data
        }
    )
