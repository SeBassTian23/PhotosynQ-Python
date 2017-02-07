import requests
import getpass
import json

api_url = "https://photosynq.org/api/v3/"
user_email = None
auth_token = None

def getJsonContent( response ):
    return json.loads( response.content.decode('utf-8') )

def logout():
    global auth_token
    global user_email
    if auth_token is None:
        raise Exception( "not logged in." )
    r = requests.delete(api_url + "/sign_out.json", data = { "auth_token":auth_token } )
    content = getJsonContent( r )
    if "notice" in content.keys():
        print( content["notice"] )
    auth_token = None
    user_email = None

def login():
    global auth_token
    global user_email
    if auth_token is not None:
        raise Exception( "already logged in as " + user_email + ". Use logout() to logout before logging in again" )
    user_email = input( "enter your email: " )
    password = getpass.getpass( "enter your password: " )
    r = requests.post( api_url + "/sign_in.json", data = { "user[email]":user_email,"user[password]":password } )
    if r.status_code == 500:
        raise Exception( "invalid email/password combination" )
    content = getJsonContent( r )
    if "error" in content.keys():
        raise Exception( content["error"] )
    auth_token = content["user"]["auth_token"]
    

def getProjectInfo( projectId ):
    if auth_token is None:
        raise Exception( "not logged in." )
    r = requests.get(api_url + "/projects/" + str(projectId) + ".json", data = { "user_token":auth_token, "user_email":user_email } )
    content = getJsonContent( r )
    return content;
    
def getProjectData( projectId ):
    if auth_token is None:
        raise Exception( "not logged in." )
    r = requests.get(api_url + "/projects/" + str(projectId) + "/data.json", data = { "user_token":auth_token, "user_email":user_email, "upd":True } )
    content = getJsonContent( r )
    return content;
        
def buildProjectDataFrame( project_info, project_data ):
    if project_info is None:
        raise Exception( "Project info missing" )
    if project_data is None:
        raise Exception( "Project data missing" )

    # Print Project data receival information
    print("Project data received, generating dataframe.")
    
    # Exclusion list
    ToExclude = ["protocol_number","protocol_id","id","protocol_name","baseline_values","chlorophyll_spad_calibration","averages","data_raw","baseline_sample","HTML","Macro","GraphType","time","time_offset","get_ir_baseline","get_blank_cal","get_userdef0","get_userdef1","get_userdef2","get_userdef3","get_userdef4","get_userdef5","get_userdef6","get_userdef7","get_userdef8","get_userdef9","get_userdef10","get_userdef11","get_userdef12","get_userdef13","get_userdef14","get_userdef15","get_userdef16","get_userdef17","get_userdef18","get_userdef19","get_userdef20","r","g","b","recall","messages","order"]
    
    # Since we have all the information ready
    # now it is time to preprocess the data
    
    # Let's count the protocols first, to see which ones we actually need
    # and generate a lookup table
    protocols = {}
    for protocol in project_info["protocols"]:
        protocols[str(protocol["id"])] = { "name": protocol["name"], parameters: [], "count": 0 }
    
    # Add counter for custom data
    protocols["custom"] = { "name":"Imported Data (Custom Data)", parameters:[], "count":0 }
    
    # Now we work on the actual data
    for sampleindex in project_data:
    
        # Remove data entries that don't have the sample key
        if not "sample" in sampleindex.keys():
            # sampleindex = NULL
            continue
    
        # We skip the time changes for now
        # TODO: Implement the new timestamps here
    
        # Make sure location is false or an array
#        if "location" in sampleindex.keys():
#            if(typeof(sampleindex$location) == "character"){
#                sampleindex$location <- strsplit(sampleindex$location,",")
#            }
    
#        if "time" in sampleindex.keys():
#            sampleindex$time <- sampleindex$time
    
        # Make sure answers are an array
        if not "user_answers" in sampleindex.keys(): # || typeof(sampleindex$user_answers) == "character")
            sampleindex["user_answers"] = {}
    
        # Loop through measurements of one sample
        for sampleprotocol in sampleindex["sample"]:
    
            # Skip Measurements without protocol id
            if not "protocol_id" in sampleprotocol.keys():
                continue
    
            # Correct timestamp
            if not "time" in sampleprotocol.keys():
                sampleprotocol["time"] = sampleindex["time"]
    
            # Build the user answers
            answers = {}
            for filters in project_info["filters"]:
                answers["answer_"+str(filters["id"])] = filters["label"]
    
            protocols[str(sampleprotocol["protocol_id"])]["parameters"] = [protocols[str(sampleprotocol["protocol_id"])]["parameters"], sampleprotocol.keys()]
    
            # Add Dummy for unknown protocols
            if not str(sampleprotocol["protocol_id"]) in protocols.keys():
                protocols[str(sampleprotocol["protocol_id"])] = { "name": "Unknown Protocol (ID: " + sampleprotocol["protocol_id"] + ")", "parameters": [], "count": 0 }
            else:
                if not "count" in protocols[str(sampleprotocol["protocol_id"])].keys():
                    protocols[str(sampleprotocol["protocol_id"])]["count"] = 1
                else:
                    protocols[str(sampleprotocol["protocol_id"])]["count"] = protocols[str(sampleprotocol["protocol_id"])]["count"] + 1
    
            # Check if there is custom data
            if "custom" in sampleindex.keys():
                protocols["custom"] = protocols["custom"] + 1

    
    for p in protocols.keys():
        protocols[p]["parameters"] = unique(protocols[p]["parameters"])
    
    # Now that the preprocessing is done, we can start putting 
    # the data into the data frame
    
    spreadsheet = {};
    for p in protocols.keys():
    
        if protocols[p]["count"] == 0:
            continue
        
        spreadsheet[p] = {}
    
        spreadsheet[p]["datum_id"] = [1]
        spreadsheet[p]["time"] = [1]
    
        for a in answers.keys():
            spreadsheet[p][a] = [1]
    
        # Add the protocol to the list
        for i in range( 1, len(protocols[p]["parameters"])):
            if not str(protocols[p]["parameters"][i]) in ToExclude:
                spreadsheet[p][str(protocols[p]["parameters"][i])] = [1]
    
        spreadsheet[p]["user_id"] = [1]
        spreadsheet[p]["device_id"] = [1]
        spreadsheet[p]["status"] = [1]
        spreadsheet[p]["notes"] = [1]
        spreadsheet[p]["longitude"] = [1]
        spreadsheet[p]["latitute"] = [1]
    
    for measurement in project_data:
        for prot in measurement["sample"]:
            protocolID = str(prot["protocol_id"])
            for param in spreadsheet["protocolID"].keys():
    
                if param == "datum_id":
                    spreadsheet[protocolID]["datum_id"] = [ spreadsheet[protocolID]["datum_id"], measurement["datum_id"] ]
                        
                elif param == "time":
                    time <- as.POSIXlt( ( as.numeric(prot[[toString(param)]]) / 1000 ), origin="1970-01-01" )
                    spreadsheet[protocolID]["time"] = [ spreadsheet[protocolID]["time"], str(time) ]
                        
                elif param == "user_id":
                    spreadsheet[protocolID]["user_id"] = [ spreadsheet[protocolID]["user_id"], str(measurement["user_id"]) ]
                        
                elif param == "device_id":
                    spreadsheet[protocolID]["device_id"] = [ spreadsheet[protocolID]["device_id"], str(measurement["device_id"]) ]
                          
                elif param == "longitude":
                    spreadsheet[protocolID]["longitude"] = [ spreadsheet[protocolID]["longitude"], str(measurement["location"][1]) ]                                                        
    
                elif param == "latitute":
                    spreadsheet[protocolID]["latitute"] = [ spreadsheet[protocolID]["latitute"], str(measurement["location"][2]) ]
    
                elif param == "notes":
                    spreadsheet[protocolID]["notes"] = [ spreadsheet[protocolID]["notes"], str(measurement["note"]) ]
    
                elif param == "status":
                    spreadsheet[protocolID]["status"] = [ spreadsheet[protocolID]["status"], str(measurement["status"]) ]
    
                elif substr(param,0,7) == "answer_":
                    answer <- strsplit(param,"_")[[1]][2]
                    spreadsheet[protocolID][param]] = [spreadsheet[protocolID][param], measurement["user_answers"][str(answer)] ]
    
                elif is.atomic(prot[[str(param)]]):
                    spreadsheet[protocolID][param] = [ spreadsheet[protocolID][param], str(prot[str(param)])]
                else:
                    spreadsheet[protocolID][param] = [ spreadsheet[protocolID][param], prot[str(param)]]
            }
    
        }
    
    }
    
    # Stupid, but we have to do this to remove the first row
    for(protocol in names(spreadsheet)){
        ii <- 1
        for(parameter in names(spreadsheet[[protocol]])){
            len <- length(spreadsheet[[protocol]][[parameter]])
            spreadsheet[[protocol]][[parameter]] <- spreadsheet[[protocol]][[parameter]] [2:len]
    
            if(!is.null(answers[[parameter]])){
                names(spreadsheet[[protocol]])[ii] <- answers[[parameter]]
            }
            ii <- ii + 1
        }
    }
    
    i <- 1
    for(protocol in names(spreadsheet)){
        if(!is.null(protocols[[toString(protocol)]]$name)){
            names(spreadsheet)[i] <- protocols[[toString(protocol)]]$name
        }
        i <- i + 1
    }
    
    return(spreadsheet)