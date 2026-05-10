from django.db import models


class Metric(models.Model):

    device_id = models.CharField(max_length=100)
    ip = models.CharField(max_length=100)

    cpu = models.FloatField()
    memory = models.FloatField()
    disk = models.FloatField()

    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.device_id