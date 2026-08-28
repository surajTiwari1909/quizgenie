from django.contrib import admin

from profiles.models import Profile


# Register the Profile model with the Django Admin site.
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    # Define the columns displayed on the Profile list page
    # in the Django Admin panel.
    list_display = ("id", "user", "created_at", "updated_at")

    # Enable searching profiles using fields from the related User model.
    # `user__username` searches by the user's username.
    # `user__email` searches by the user's email.
    # `__` is used by Django ORM to access fields of a related model.
    search_fields = ("user__username", "user__email")

    # Display the `user` relationship as an ID lookup field instead
    # of loading all users into a dropdown.
    # This is more efficient when the application has many users.
    raw_id_fields = ("user",)

    """
    Because "user__email" is Django ORM lookup syntax, 
    while user.email is normal Python object-access syntax. 
    They are used in different situations.

    For example, imagine:

Profile → User → Company → Address → City

In Python:

profile.user.company.address.city

In a Django ORM lookup:

user__company__address__city
    """
