import factory
from django.contrib.auth import get_user_model

PASSWORD = "Str0ng-Pass!word"


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = get_user_model()
        skip_postgeneration_save = True

    email = factory.Sequence(lambda n: f"user{n}@forge.test")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    role = "student"
    is_active = True

    @factory.post_generation
    def password(obj, create, extracted, **kwargs):  # noqa: N805
        obj.set_password(extracted or PASSWORD)
        if create:
            obj.save()
