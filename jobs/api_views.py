from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import JobRequest, JobMatch
from .serializers import JobSerializer, JobMatchSerializer

class JobViewSet(viewsets.ModelViewSet):
    """API endpoint for jobs"""
    serializer_class = JobSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.profile.user_type == 'employer':
            return JobRequest.objects.filter(employer=self.request.user)
        elif self.request.user.profile.user_type == 'worker':
            return JobRequest.objects.filter(status='open')
        return JobRequest.objects.none()
    
    def perform_create(self, serializer):
        serializer.save(employer=self.request.user)
    
    @action(detail=True, methods=['post'])
    def apply(self, request, pk=None):
        job = self.get_object()
        if request.user.profile.user_type != 'worker':
            return Response({'error': 'Only workers can apply'}, status=status.HTTP_400_BAD_REQUEST)
        
        match, created = JobMatch.objects.get_or_create(
            job_request=job,
            worker=request.user,
            defaults={'status': 'pending'}
        )
        
        if created:
            return Response({'message': 'Application submitted successfully'})
        return Response({'message': 'Already applied'})