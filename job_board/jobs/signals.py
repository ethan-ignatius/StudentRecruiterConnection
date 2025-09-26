from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import Job
from .geocoding import geocode_city_state

@receiver(pre_save, sender=Job)
def set_job_coords_on_change(sender, instance: Job, **kwargs):
    loc = (instance.location or "").strip()

    # handle remote/blank
    if not loc or loc.lower().startswith("remote"):
        instance.latitude = None
        instance.longitude = None
        return

    parts = [p.strip() for p in loc.split(",")]
    if len(parts) < 2:
        return
    city, state = parts[0], parts[1]

    needs_geocode = False
    try:
        old = Job.objects.get(pk=instance.pk)
    except Job.DoesNotExist:
        old = None

    if old is None:
        needs_geocode = True                        
    else:
        if (old.location or "").strip() != loc:
            needs_geocode = True                    
        if instance.latitude is None or instance.longitude is None:
            needs_geocode = True

    if needs_geocode:
        latlng = geocode_city_state(city, state)
        if latlng:
            instance.latitude, instance.longitude = latlng
        else:
            instance.latitude = None
            instance.longitude = None