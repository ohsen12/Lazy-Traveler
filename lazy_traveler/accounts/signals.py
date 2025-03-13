from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import Profile

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    tags_list = []
    if instance.tags:
        tags_list = [tag.strip() for tag in instance.tags.split(',') if tag.strip()]
    
    # update_or_create를 사용하면, Profile이 존재하면 업데이트, 없으면 생성
    Profile.objects.update_or_create(
        user=instance,
        defaults={'recommendation_keywords': tags_list}
    )
