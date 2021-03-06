import requests
import yaml
import json
import csv
import os
import time
import random
import math
from pathos.multiprocessing import ProcessingPool as Pool


'''
def distance(geocode1, geocode2):
    R = 6373.0

    lat1 = math.radians(geocode1[0])
    lon1 = math.radians(geocode1[1])
    lat2 = math.radians(geocode2[0])
    lon2 = math.radians(geocode2[1])

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    distance = R * c
    return distance


def testaccuracy(loc, radius):
    gm = GMaps()
    geocode = gm.geocode(loc)

    for i in range(10):
        print(distance((geocode['lat'], geocode['lng']), location(geocode, radius)))
'''


def random_location(geocode, radius):
    rd = radius / 11300
    u, v = random.uniform(0.0, 1.0), random.uniform(0.0, 1.0)
    w = rd * math.sqrt(u)
    t = 2 * math.pi *  v
    x = w * math.cos(t)
    y = w * math.sin(t)

    return {'lat': float(geocode['lat']) + y, 'lng': float(geocode['lng']) + x}



class GMaps:
    def __init__(self, APIKey=None):
        if not APIKey:
            APIKey = self.getAPIKey()
        self.APIKey = APIKey


    @staticmethod
    def getAPIKey():
        if 'GoogleAPIKey' in os.environ:
            APIKey = os.environ['GoogleAPIKey']
        else:    
            with open('creds.yaml') as file:
                creds = yaml.load(file)
            APIKey = creds['Google']['APIKey']
        return APIKey


    def geocode(self, address):
        ENDPOINT = 'https://maps.googleapis.com/maps/api/geocode/json'
        params = {'address': address, 'key': self.APIKey}
        response = requests.get(ENDPOINT, params=params)

        code = response.json()['results'][0]['geometry']['location']
        return code


    def get_details(self, place_id):
        ENDPOINT = 'https://maps.googleapis.com/maps/api/place/details/json'
        params = {'key': self.APIKey, 'placeid': place_id}
        response = requests.get(ENDPOINT, params=params).json()

        try:
            phone_number = response['result']['international_phone_number']
        except KeyError:
            phone_number = None
        try:
            website = response['result']['website']
        except KeyError:
            website = None

        result = {
            'phone_number': phone_number,
            'website': website
        }
        return result



    def places(self, query, geocode, radius, min_rating=None, max_rating=None):
        ENDPOINT = 'https://maps.googleapis.com/maps/api/place/textsearch/json'
        params = {
            'key': self.APIKey,
            'location': '{},{}'.format(geocode['lat'], geocode['lng']),
            'radius': radius,
            'query': query
        }
        
        results = []
        while True:
            places = requests.get(ENDPOINT, params=params).json()
            results = results + places['results']
            try:
                next_page_token = places['next_page_token']
            except KeyError:
                break
            params['pagetoken'] = next_page_token
            time.sleep(2)
        
        parsed = []
        for result in results:
            try:
                rating = result['rating']
            except KeyError:
                rating = 0.0

            entry = {
                'id': result['place_id'],
                'name': result['name'],
                'geocode': str(result['geometry']['location']['lat']) + ',' + str(result['geometry']['location']['lng']),
                'rating': rating,
                'address': result['formatted_address']
            }
            parsed.append(entry)

        if min_rating:
            parsed =  [x for x in parsed if x['rating'] >= min_rating]
        if max_rating:
            parsed =  [x for x in parsed if x['rating'] <= max_rating]
        return parsed


    def search(self, query, location, radius, points=1, min_rating=None, max_rating=None):
        code = self.geocode(location)
        codes = []

        for i in range(points):
            codes.append(code)
            code = random_location(code, radius)

        fun = lambda x: self.places(query, x, radius, min_rating, max_rating)
        with Pool(10) as p:
            results = p.map(fun, codes)

        flat = [item for sublist in results for item in sublist]
        results = list({i['id']:i for i in reversed(flat)}.values())
            
        for entry in results:
            entry.update(self.get_details(entry['id']))

        return results


def save(listings, filename):
    with open('listings/' + filename, 'w', newline='') as csvfile:
        fieldnames = ['id', 'name', 'geocode', 'rating', 'address', 'phone_number', 'website']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')

        writer.writeheader()
        for listing in listings:
            writer.writerow(listing)


def main():
    gmaps = GMaps()
    query = input('[*] Search query: ')
    location = input('[*] Location: ')
    radius = int(input('[*] Radius (in meters): '))
    points = int(input('[*] Number of points to take: '))
    try:
        min_rating = float(input('[*] Minimum rating (optional): '))
    except TypeError:
        min_rating = None
    try:
        max_rating = float(input('[*] Maximum rating (optional): '))
    except TypeError:
        max_rating = None
    
    places = gmaps.search(query, location, radius, points, min_rating, max_rating)
    save(places, 'listings.csv')
    print()
    print('[*] {} places scraped. Saved in listings.csv'.format(len(places)))



if __name__=='__main__':
    main()
