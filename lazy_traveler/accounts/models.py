from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinValueValidator, MaxValueValidator


class Place(models.Model):
    name = models.CharField(max_length=50)
    tags = ArrayField(models.CharField(max_length=50, blank=True, default=list))
    address = models.CharField(max_length=255)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    rating = models.FloatField(
        null=True, 
        blank=True,
        default=0.0,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        help_text="0~5 범위의 평점")
    place_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    website = models.URLField(null=True, blank=True)
    opening_hours = ArrayField(models.CharField(max_length=255, null=True, blank=True))
    
    class Meta:
        unique_together = ('name', 'address')
    
    def __str__(self):
        return self.name


class User(AbstractUser):
    username = models.CharField(max_length=50, unique=True)  # username 필드 중복 방지
    password = models.CharField(max_length=128) 
    created_at = models.DateTimeField(auto_now_add=True)
    # 쉼표(,)로 구분된 문자열(ex."맛집,카페,한식") 저장. 저장된 값을 쉼표로 분리해서 리스트로 변환할 수 있음. 
    # 프론트엔드에서는 이를 "맛집,카페,한식" 이런 식으로 하나의 문자열로 서버에 전송해야 함.
    tags = ArrayField(models.CharField(max_length=50, blank=True, default=list)) # 추후에 JSON필드로
    selected_places = models.ManyToManyField(Place, blank=True)