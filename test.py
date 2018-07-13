from __future__ import division
from time import sleep
import httplib2
import json


h = httplib2.Http()

url = raw_input("Please enter the uri you want to access:   ")
if url == '':
	url = 'http://localhost:8080/api/v1/users'


req_per_minute = float(raw_input("Please specify the number of requests per minute:  ") )


interval = (60.0 / req_per_minute)

def SendRequests(url, req_per_minute):
	requests = 0 
	while requests < req_per_minute:
		result = json.loads(h.request(url,'GET')[1])
		#result = h.request(url,'GET')[1]
		#print result
		if result.get('error') is not None:
			print "Error #%s : %s" %(result.get('error'), result.get('data'))
			print "Hit rate limit. Waiting 5 seconds and trying again..."
			sleep(5)
			SendRequests(url, req_per_minute)
		else:
			print  "Number of Requests: ", requests+1 
			print result.get('response')
		requests = requests + 1 
		sleep(interval)

print "Sending Requests..."
SendRequests(url, req_per_minute)