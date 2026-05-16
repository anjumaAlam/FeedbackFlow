def notifications_count(request):
    if request.user.is_authenticated:
        from users.models import Notification, Announcement
        count = Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count()

        # OR 2.11: Get active announcements visible to this user
        active_announcements = []
        for ann in Announcement.objects.filter(is_active=True).order_by('-created_at')[:10]:
            if ann.is_visible_to(request.user):
                active_announcements.append(ann)
            if len(active_announcements) >= 3:
                break

        return {
            'unread_notifications_count': count,
            'active_announcements': active_announcements,
        }
    return {'unread_notifications_count': 0, 'active_announcements': []}