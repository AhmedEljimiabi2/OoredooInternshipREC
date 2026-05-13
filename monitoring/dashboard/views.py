from django.shortcuts import render
from django.http import JsonResponse

from django.contrib.auth.decorators import login_required

from .models import Metric

from datetime import timedelta
from django.utils.timezone import now


@login_required
def index(request):

    return render(
        request,
        'dashboard/index.html'
    )


@login_required
def history(request, device_id):

    minutes = int(
        request.GET.get('minutes', 60)
    )

    cutoff = now() - timedelta(minutes=minutes)

    rows = Metric.objects.filter(
        device_id=device_id,
        timestamp__gte=cutoff
    ).order_by('timestamp')

    data = []

    for r in rows:

        data.append({
            'cpu': r.cpu,
            'memory': r.memory,
            'disk': r.disk,
            'timestamp': r.timestamp.isoformat()
        })

    return JsonResponse(data, safe=False)