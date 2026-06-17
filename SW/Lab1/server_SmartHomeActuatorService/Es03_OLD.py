import cherrypy
import random
import json
import time
from datetime import datetime, timezone

import requests

class SmartHomeActuatorService(object):
    exposed = True
    
    url_log = "http://127.0.0.1:9092/log/"

    rooms_act = {"living_room": {
                        "thermostat": None,
                        "lights": None,
                        "blinds": None},
            "kitchen": {
                        "thermostat": None,
                        "lights": None,
                        "blinds": None},
            "bedroom": {
                        "thermostat": None,
                        "lights": None,
                        "blinds": None},
            }
    
    units = {
        "thermostat": "Cel",
        "lights": "bool",
        "blinds": "pct"
    }
    
    ## Funzione per inizializzare la classe, utile per la simulazione, in questo modo i sensori hanno già dei valori random al primo avvio del server
    def __init__(self):
        self.InitAct()

    ## Funzione che gestisce le richieste GET, in base alla presenza o meno di parametri e alla loro tipologia (URI o query parameters) decide quale funzione chiamare per ottenere i dati richiesti  
    def GET(self, *uri, **params):
        if(len(uri) == 0 and len(params) != 0):
            keys = list(params.keys())
            if (len(keys) == 1 and keys[0] == "room"):
                response = self.get_room(params["room"])
            elif (len(keys) == 2 and keys[0] == "room" and keys[1] == "act"):
                response = self.get_room_act(params["room"], params["act"])
            else:
                raise cherrypy.HTTPError(400, "Bad request: Invalid query parameters. Valid parameters are 'room' and 'act'. Example: ?room=living_room&act=thermostat")

        elif(len(params) == 0):
            if(len(params) == 0 and len(uri)==0):
                response = self.get_allAct()
            elif(len(uri)==1):
                response = self.get_room(uri[0])
            elif(len(uri)==2):
                response = self.get_room_act(uri[0], uri[1])
            else:
                raise cherrypy.HTTPError(400, "Bad request: Invalid URI format. Valid formats are /actuators/, /actuators/{room}, /actuators/{room}/{act}. Example: /actuators/living_room/thermostat")

        return json.dumps(response).encode("utf-8")
    
    #STRUTTURA DEL BODY DA INVIARE PER AGGIORNARE UN ATTUATORE: 
    #{
    #    "bn": "kitchen/",
    #    "e": [
    #        {
    #        "n": "lights",
    #        "v": True,
    #        "u": "bool"
    #        }
    #    ]
    #}
    
    ## Funzione che gestisce le richieste PUT, si aspetta un body in formato JSON con i campi bn (base name), e (array di elementi) dove ogni elemento deve contenere i campi n (name), v (value) e u (unit). In base al contenuto del body aggiorna il valore dell'attuatore specificato e aggiunge un log della modifica effettuata
    def PUT(self, *uri, **params):
        
        # Controllo che il Content-Type sia application/json, altrimenti ritorna un errore 415 Unsupported Media Type
        if cherrypy.request.headers.get("Content-Type", "") != "application/json":
            raise cherrypy.HTTPError(415, "Bad request: Content-Type must be application/json")
        
        if(len(uri) == 0):
            raw = cherrypy.request.body.read()
            
            # Controllo correttezza del pacchetto
            if not raw:
                raise cherrypy.HTTPError(400, "Bad request: Empty body")
            
            try:
                body = json.loads(raw)
            except json.JSONDecodeError:
                raise cherrypy.HTTPError(400, "Bad request: Invalid JSON body")
            
            #controllo che il pacchetto contenga i campi necessari (bn, e) e che e sia una lista con almeno un elemento che contenga i campi n, v, u
            
            if "bn" not in body or "e" not in body:
                raise cherrypy.HTTPError(422, "Bad request: Unprocessable Entity")
            
            if not isinstance(body["e"], list):
                raise cherrypy.HTTPError(422, "Bad request: Unprocessable Entity")
            
            if len(body["e"]) != 1:
                raise cherrypy.HTTPError(422, "Bad request: Unprocessable Entity")
            
            if len(body["e"][0]) != 3:
                raise cherrypy.HTTPError(422, "Bad request: Unprocessable Entity")
            
            if "n" not in body["e"][0] or "v" not in body["e"][0] or "u" not in body["e"][0]:
                raise cherrypy.HTTPError(422, "Bad request: Unprocessable Entity")
            
            room = body["bn"].rstrip('/')  # Rimuove eventuale slash finale
            sensor = body["e"][0]["n"]
            value = body["e"][0]["v"]
            
            # Controllo che la stanza e il sensore esistano, altrimenti ritorna un errore 404 Not Found
            # Controllo che il valore sia corretto (es. se è un termostato deve essere compreso tra 10 e 30, se sono le luci deve essere on o off, se sono le tapparelle deve essere compreso tra 0 e 100), altrimenti ritorna un errore 400 Bad Request
             
            if room not in self.rooms_act:
                raise cherrypy.HTTPError(404, "Room not found")
            
            if sensor not in self.rooms_act[room]:
                raise cherrypy.HTTPError(404, "Sensor not found in this room")
                
            # Controllo correttezza value (se in range)
             
            if sensor == "thermostat":
                if value < 10 or value > 30:
                    raise cherrypy.HTTPError(400, "Bad request: Value out of range for thermostat (10-30)")
            elif sensor == "lights":
                if value != True and value != False:
                    raise cherrypy.HTTPError(400, "Bad request: Value for lights must be True or False")
            elif sensor == "blinds":
                if value < 0 or value > 100:
                    raise cherrypy.HTTPError(400, "Bad request: Value out of range for blinds (0-100)")

            self.rooms_act[room][sensor] = value
            # Aggiunta del Json nel log
            self.send_log(room, sensor, value)

            return json.dumps(self.get_room_act(room, sensor)).encode("utf-8")

    ## Funzione per inizializzare gli attuatori con valori random, utile per la simulazione
    def InitAct(self):
        for room in self.rooms_act.values():
            for sens in room.keys():
                if(sens == "temperature" or sens == "humidity"):
                    room[sens] = random.uniform(10, 40)
                elif(sens == "motion_sensor"):
                    room[sens] = random.choice([True, False])
    
    ## funzione per inviare un log al server di log, in caso di fallimento dell'invio ritorna un errore 500 Internal Server Error; il log contiene la stanza, il sensore, il nuovo valore e l'unità di misura
    def send_log(self, room, sensor, value):
        timestamp = time.time()
        payload = {
            "bn": room + '/' + sensor + '/',
            "bt": timestamp,
            "e": [
                {
                    "n": "status",
                    "v": value,
                    "u": self.units.get(sensor, None)
                }
            ]
        }

        # Invia il log al server di log via POST; se fallisce, lo salva localmente
        try:
            resp = requests.post(self.url_log, json=payload, headers={"Content-Type": "application/json"}, timeout=5)
            if resp.status_code not in (200, 201):
                raise cherrypy.HTTPError(404, json.dumps({"error": "Failed to send log to log server, status code: " + str(resp.status_code)}))

        except Exception:
            raise cherrypy.HTTPError(500, json.dumps({"error": "Failed to send log"}))

    ## Funzione per ottenere tutti i sensori di tutte le stanze, utile per il GET senza parametri    
    def get_allAct(self):
        response = []
        for room in self.rooms_act:
            response.append(self.get_room(room))
        
        return response
    
    ## Funzione per ottenere tutti i sensori di una stanza, utile per il GET con un parametro (nome stanza)
    def get_room(self, room):
        if(room not in self.rooms_act):
            raise cherrypy.HTTPError(404, json.dumps({"error": "room not found", "available_rooms": list(self.rooms_act.keys())}))
        
        timestamp = time.time()   
        elem = []
        
        # Creazione del pacchetto SenML con tutti i sensori della stanza
        for sens in self.rooms_act[room]:
            elem.append(
                {
                    "n": sens,
                    "v": self.rooms_act[room][sens],
                    "u": self.units.get(sens, None)
                }
            )
        
        response = {
            "bn": room + '/',
            "bt": timestamp,
            "e": elem
        }

        return response
    
    # Funzione per ottenere il valore di un sensore specifico in una stanza specifica, utile per il GET con due parametri (nome stanza e nome sensore)
    def get_room_act(self, room, sens):
        if(room not in self.rooms_act):
            raise cherrypy.HTTPError(404, json.dumps({"error": "room not found", "available_rooms": list(self.rooms_act.keys())}))

        if(sens not in self.rooms_act[room]):
            raise cherrypy.HTTPError(400, json.dumps({"error": "unknown actuator type", "valid_types": list(self.rooms_act[room].keys())}))

        timestamp = time.time()

        response = {
            "bn": room + '/',
            "bt": timestamp,
            "e": [
                {
                    "n": sens,
                    "v": self.rooms_act[room][sens],
                    "u": self.units.get(sens, None)
                }
            ]
        }
        return response