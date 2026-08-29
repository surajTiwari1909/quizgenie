from django.contrib import admin

from multiplayer.models import Contest, ContestAnswer, ContestParticipant


@admin.register(Contest)
class ContestAdmin(admin.ModelAdmin):
    list_display = ("code", "quiz", "host", "status", "max_players", "created_at")
    list_filter = ("status",)
    search_fields = ("code", "quiz__title", "host__username")
    raw_id_fields = ("host", "quiz")
    readonly_fields = ("created_at", "started_at", "completed_at")


@admin.register(ContestParticipant)
class ContestParticipantAdmin(admin.ModelAdmin):
    list_display = ("contest", "user", "score", "joined_at")
    raw_id_fields = ("contest", "user")
    readonly_fields = ("joined_at",)


@admin.register(ContestAnswer)
class ContestAnswerAdmin(admin.ModelAdmin):
    list_display = ("participant", "question", "is_correct", "awarded_points")
    raw_id_fields = ("participant", "question", "selected_option")
    readonly_fields = ("answered_at",)
