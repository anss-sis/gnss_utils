'''
custom_exceptions.py 
v1.0 
2021-02-09

Contains basic exception classes that can be expanded if needed. 
    
Author: Prabha Acharya, ANSS SIS Development Team, SCSN
Email: sis-help@gps.caltech.edu
'''
class ParseException(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return "%s: %s" % (self.__class__.__name__, self.value)