from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from theatre.models import (
    Actor,
    Genre,
    Performance,
    Play,
    Reservation,
    TheatreHall,
    Ticket,
)


class TheatreCatalogueApiTests(APITestCase):
    def setUp(self):
        self.genre = Genre.objects.create(name="Drama")
        self.actor = Actor.objects.create(first_name="Mark", last_name="Rylance")
        self.play = Play.objects.create(title="Jerusalem", description="A play")
        self.play.genres.add(self.genre)
        self.play.actors.add(self.actor)
        self.hall = TheatreHall.objects.create(
            name="Grand Hall",
            rows=2,
            seats_in_row=3,
        )
        self.performance = Performance.objects.create(
            play=self.play,
            theatre_hall=self.hall,
            show_time=timezone.now() + timedelta(days=1),
        )

    def test_anonymous_visitor_can_browse_plays(self):
        response = self.client.get(reverse("theatre:play-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["title"], "Jerusalem")
        self.assertEqual(response.data["results"][0]["genres"], ["Drama"])

    def test_play_list_can_be_filtered(self):
        Play.objects.create(title="Comedy Night", description="Another play")

        response = self.client.get(
            reverse("theatre:play-list"),
            {"title": "jeru", "genres": str(self.genre.id)},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], self.play.id)

    def test_non_admin_cannot_modify_catalogue(self):
        user = get_user_model().objects.create_user(
            email="visitor@example.com",
            password="secure-pass-123",
        )
        self.client.force_authenticate(user)

        response = self.client.post(
            reverse("theatre:genre-list"),
            {"name": "Comedy"},
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_modify_catalogue(self):
        admin = get_user_model().objects.create_superuser(
            email="admin@example.com",
            password="secure-pass-123",
        )
        self.client.force_authenticate(admin)

        response = self.client.post(
            reverse("theatre:genre-list"),
            {"name": "Comedy"},
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Genre.objects.filter(name="Comedy").exists())

    def test_performance_list_reports_available_seats(self):
        user = get_user_model().objects.create_user(
            email="booked@example.com",
            password="secure-pass-123",
        )
        reservation = Reservation.objects.create(user=user)
        Ticket.objects.create(
            row=1,
            seat=1,
            performance=self.performance,
            reservation=reservation,
        )

        response = self.client.get(reverse("theatre:performance-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"][0]["available_seats"], 5)


class ReservationApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="booker@example.com",
            password="secure-pass-123",
        )
        self.other_user = get_user_model().objects.create_user(
            email="other@example.com",
            password="secure-pass-123",
        )
        play = Play.objects.create(title="King Lear", description="A tragedy")
        hall = TheatreHall.objects.create(name="Studio", rows=2, seats_in_row=2)
        self.performance = Performance.objects.create(
            play=play,
            theatre_hall=hall,
            show_time=timezone.now() + timedelta(days=2),
        )
        self.url = reverse("theatre:reservation-list")

    def test_authenticated_user_can_reserve_available_seats(self):
        self.client.force_authenticate(self.user)

        response = self.client.post(
            self.url,
            {
                "tickets": [
                    {
                        "row": 1,
                        "seat": 1,
                        "performance": self.performance.id,
                    },
                    {
                        "row": 1,
                        "seat": 2,
                        "performance": self.performance.id,
                    },
                ]
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        reservation = Reservation.objects.get(user=self.user)
        self.assertEqual(reservation.tickets.count(), 2)

    def test_seat_cannot_be_reserved_twice(self):
        reservation = Reservation.objects.create(user=self.other_user)
        Ticket.objects.create(
            row=1,
            seat=1,
            performance=self.performance,
            reservation=reservation,
        )
        self.client.force_authenticate(self.user)

        response = self.client.post(
            self.url,
            {
                "tickets": [
                    {
                        "row": 1,
                        "seat": 1,
                        "performance": self.performance.id,
                    }
                ]
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Reservation.objects.filter(user=self.user).exists())

    def test_seat_outside_hall_is_rejected(self):
        self.client.force_authenticate(self.user)

        response = self.client.post(
            self.url,
            {
                "tickets": [
                    {
                        "row": 3,
                        "seat": 1,
                        "performance": self.performance.id,
                    }
                ]
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Reservation.objects.count(), 0)

    def test_user_only_sees_own_reservations(self):
        Reservation.objects.create(user=self.user)
        Reservation.objects.create(user=self.other_user)
        self.client.force_authenticate(self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_reservations_require_authentication(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
