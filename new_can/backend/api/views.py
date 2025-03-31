from django.shortcuts import render
from .serializers import(
    ListAPIView,
    CreateAPIView
)
from django.views import View
from django.http import HttpResponse
from django.http.response import JsonResponse
from rest_framework.decorators import parser_classes
from rest_framework.parsers import MultiPartParser, JSONParser
from rest_framework import status
from rest_framework.decorators import api_view
import cantools
import can
import json
import logging


@api_view(['POST'])
@parser_classes([FiledUploadParser, JSONParser])
def upload_file(request):
    file=request.FILES['data']
    dbc_file_data=file.read()

    db.input={'FileName':file.name,
              'FileData':dbc_file_data.decode('utf-8')

    }



class displayDataView(View):