from django.contrib import admin

from theatre.models import (
    Actor,
    Genre,
    Performance,
    Play,
    Reservation,
    TheatreHall,
    Ticket,
)


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    search_fields = ("name",)


@admin.register(Actor)
class ActorAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name")
    search_fields = ("first_name", "last_name")


@admin.register(Play)
class PlayAdmin(admin.ModelAdmin):
    list_display = ("title",)
    search_fields = ("title",)
    filter_horizontal = ("genres", "actors")


@admin.register(TheatreHall)
class TheatreHallAdmin(admin.ModelAdmin):
    list_display = ("name", "rows", "seats_in_row", "capacity")


@admin.register(Performance)
class PerformanceAdmin(admin.ModelAdmin):
    list_display = ("play", "theatre_hall", "show_time")
    list_filter = ("theatre_hall", "show_time")
    search_fields = ("play__title",)


class TicketInline(admin.TabularInline):
    model = Ticket
    extra = 0
    readonly_fields = ("performance", "row", "seat")


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__email",)
    inlines = (TicketInline,)


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("performance", "row", "seat", "reservation")
    list_filter = ("performance",)
