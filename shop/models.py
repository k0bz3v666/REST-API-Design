from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Brand(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    country = models.CharField(max_length=60, blank=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    class AnimalType(models.TextChoices):
        CAT = "cat", "Кіт"
        DOG = "dog", "Собака"
        RODENT = "rodent", "Гризун"
        BIRD = "bird", "Птах"
        FISH = "fish", "Рибки"

    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    animal_type = models.CharField(max_length=20, choices=AnimalType.choices)
    weight = models.CharField(max_length=30, blank=True)
    stock = models.PositiveIntegerField(default=0)
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="products"
    )
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, related_name="products")

    def __str__(self):
        return self.name
