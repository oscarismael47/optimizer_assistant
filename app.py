import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import Draw
import uuid
from agent.agent import invoke

st.title("Optimizer Assistant")

if "chat_id" not in st.session_state:
    st.session_state.chat_id = str(uuid.uuid4())

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []
    #st.session_state.messages = [{"role": "assistant", "content": "Select points", "metadata":{"activate_map":True}}]

if "locations" not in st.session_state:
    st.session_state.locations = None

if "tsp_map_path" not in st.session_state:
    st.session_state.tsp_map_path = None




@st.dialog(title = "Mark locations", width="medium")
def select_locations(center):
    st.write("First Select origin, next desired locations")

    m = folium.Map(location=center, zoom_start=16)

    Draw(export=True).add_to(m)

    # call to render Folium map in Streamlit
    folium_data = st_folium(m, width=725)
    #st.json(folium_data)

    coordinates = []
    if "all_drawings" in folium_data:
        if folium_data["all_drawings"] is not None:
            locations = folium_data["all_drawings"]
            for location in locations:
                if location["type"] == "Feature" and location["geometry"]["type"] == "Point":
                    coordinates_value = location["geometry"]["coordinates"]
                    coordinates_value = (coordinates_value[1], coordinates_value[0])
                    coordinates.append(coordinates_value)
    st.session_state.locations = coordinates
    if st.button("Submit"):
        #coordinates_str = "\n".join(coordinates)
        #locations_message = "My locations are: " + coordinates_str
        last_message = st.session_state.messages[-1]
        last_message_role = last_message["role"]
        last_message_content = last_message["content"]
        last_message_metadata = last_message["metadata"]
        last_message_metadata["activate_map"] = False        
        st.session_state.messages[-1] = {"role":last_message_role, "content": last_message_content, "metadata":last_message_metadata}
        #st.session_state.messages.append({"role": "user", "content": locations_message, "metadata":{}})
        #st.session_state.messages.append({"role": "assistant", "content": "TSP response", "metadata":{}})
        st.rerun()




center = [21.1250077,  -101.6859605] #

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["metadata"]:
            if "activate_map" in message["metadata"]:
                if message["metadata"]["activate_map"] is True:
                    #if st.button('Enter locations'): 
                    select_locations(center)
            elif "tsp_map_path" in message["metadata"]:
                tsp_map_path = message["metadata"]["tsp_map_path"]
                with open(tsp_map_path, "r", encoding="utf-8") as f:
                    st.components.v1.html(f.read(), height=800,width= 1400)

user_message = st.chat_input("What is up?")


if st.session_state.locations is not None:
    user_message = st.session_state.locations
    st.session_state.locations = None

# React to user input
if user_message :

    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": user_message, "metadata":{}})

    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(user_message)
    
    response, interruption = invoke(user_message, thread_id=st.session_state.chat_id)
    ai_message =  response["messages"][-1].content

    if interruption is not None:
        ai_message = interruption
        metadata = {"activate_map":True}

        with st.chat_message("assistant"):
            st.markdown(ai_message)
            if st.button('Enter locations'):     
                select_locations(center)
    else:
        metadata = {}
        with st.chat_message("assistant"):
            st.markdown(ai_message)
            if "solution" in response:
                solution = response["solution"]
                if "tsp_map_path" in solution:
                    tsp_map_path = solution["tsp_map_path"]
                    with open(tsp_map_path, "r", encoding="utf-8") as f:
                        st.components.v1.html(f.read(), height=800,width= 1400)
                    metadata = {"tsp_map_path": tsp_map_path}

    st.session_state.messages.append({"role": "assistant", "content": ai_message, "metadata":metadata})


# with st.chat_message("user"):
#     st.write("Selecting desired points")

#     # center on Liberty Bell, add marker
#     m = folium.Map(location=[21.1250077,  -101.6859605], zoom_start=16)

#     Draw(export=True).add_to(m)

#     # call to render Folium map in Streamlit
#     st_data = st_folium(m, width=725)
#     st.json(st_data)
