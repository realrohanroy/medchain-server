import hashlib
from django.db import transaction
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from .models import Record
from .serializers import RecordUploadSerializer, RecordTimelineSerializer
from .pagination import StandardResultsSetPagination
from blockchain.models import BlockchainTransaction
from blockchain.services import trigger_blockchain_transaction

class RecordUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)
    
    ALLOWED_CONTENT_TYPES = ['application/pdf', 'image/jpeg', 'image/png']

    def post(self, request):
        serializer = RecordUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        uploaded_file = request.FILES.get('file_url')
        if not uploaded_file:
            return Response({"error": "file_url is required"}, status=status.HTTP_400_BAD_REQUEST)
            
        if uploaded_file.content_type not in self.ALLOWED_CONTENT_TYPES:
            return Response(
                {"error": f"Invalid file type. Allowed: {', '.join(self.ALLOWED_CONTENT_TYPES)}"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Hashing before saving
        file_hash = hashlib.sha256()
        for chunk in uploaded_file.chunks():
            file_hash.update(chunk)
            
        uploaded_file.seek(0)
        hash_hex = file_hash.hexdigest()
        
        try:
            with transaction.atomic():
                # Save Record to DB
                record = serializer.save(user=request.user, file_hash=hash_hex)
                
                # Create BlockchainTransaction
                tx = BlockchainTransaction.objects.create(
                    record=record,
                    status='PENDING'
                )
        except Exception as e:
            return Response({"error": "Failed to save record securely."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Trigger Async Process with ID only for thread safety
        trigger_blockchain_transaction(tx.id)
        
        return Response({
            "message": "Record uploaded successfully.",
            "record_id": record.id,
            "file_hash": hash_hex,
            "file_url": request.build_absolute_uri(record.file_url.url) if record.file_url else None,
            "blockchain_status": tx.status
        }, status=status.HTTP_201_CREATED)

class RecordTimelineView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        records = Record.objects.filter(user=request.user)\
            .select_related('blockchain_tx')\
            .order_by('-record_date', '-created_at')

        paginator = self.pagination_class()
        paginated_records = paginator.paginate_queryset(records, request, view=self)

        if paginated_records is not None:
            serializer = RecordTimelineSerializer(paginated_records, many=True, context={'request': request})
            return paginator.get_paginated_response(serializer.data)

        # fallback (no pagination)
        serializer = RecordTimelineSerializer(records, many=True, context={'request': request})
        return Response(serializer.data, status=200)