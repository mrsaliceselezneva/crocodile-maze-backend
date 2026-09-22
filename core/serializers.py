from rest_framework import serializers


class GameInfoSerializer(serializers.Serializer):
    name = serializers.CharField()
    message = serializers.CharField()
