from googleapiclient.discovery import build
import pymongo
import pandas as pd
import streamlit as st

import mysql.connector
from mysql.connector import errorcode

#api connection
def Api_connect():
    api_key = 'AIzaSyCOCa2G9MowGXWjfVbiDAU3rnx59Nzo0DE'
    api_service_name = 'youtube'
    api_version = 'v3'

    youtube = build('youtube', 'v3', developerKey=api_key)

    return youtube

youtube =Api_connect()

#get channel details
def get_channel_data(channel_id):
    request = youtube.channels().list(part='snippet,contentDetails,statistics',id=channel_id)

    response = request.execute()


    for i in response['items']:
        data = dict(channelName =i['snippet']['title'],
                channel_id = i['id'],
                subscribers =i['statistics']['subscriberCount'],
                views= i['statistics']['viewCount'],
                totalVideos= i['statistics']['videoCount'],
                playlistId = i['contentDetails']['relatedPlaylists']['uploads'],
                channel_description = i['snippet']['description']
                )
    return data


#get playlist ids

def get_playlist_info(channel_id):
    All_data = []
    next_page_token = None
    next_page = True
    while next_page:

        request = youtube.playlists().list(
            part="snippet,contentDetails",
            channelId=channel_id,
            maxResults=50,
            pageToken=next_page_token
            )
        response = request.execute()

        for item in response['items']: 
            data={'PlaylistId':item['id'],
                    'Title':item['snippet']['title'],
                    'ChannelId':item['snippet']['channelId'],
                    'ChannelName':item['snippet']['channelTitle'],
                    'PublishedAt':item['snippet']['publishedAt'],
                    'VideoCount':item['contentDetails']['itemCount']}
            All_data.append(data)
        next_page_token = response.get('nextPageToken')
        if next_page_token is None:
            next_page=False
    return All_data


# get playlist video ids 
def channel_videoId(channel_id):
    videos_ids =[]

    response= youtube.channels().list(id=channel_id,
                                    part ='contentDetails').execute()
    Playlist_ID= response['items'][0]['contentDetails']['relatedPlaylists']['uploads']

    response1 = youtube.playlistItems().list(
                                    part='snippet',
                                    playlistId =Playlist_ID,
                                    maxResults=50).execute()
    next_page_token = None

    while True:
        response1 = youtube.playlistItems().list(
                                    part='snippet',
                                    playlistId =Playlist_ID,
                                    maxResults=50,
                                    pageToken=next_page_token).execute()

        for i in range(len(response1['items'])):
            videos_ids.append(response1['items'][i]['snippet']['resourceId']['videoId'])
            next_page_token = response1.get('nextPageToken')
        if next_page_token is None:
            break
        
    return videos_ids

def get_video_info(videos_ids):

    video_data = []

    for video_id in videos_ids:
        request = youtube.videos().list(
                    part="snippet,contentDetails,statistics",
                    id= video_id)
        response = request.execute()

        for item in response["items"]:
            data = dict(Channel_Name = item['snippet']['channelTitle'],
                        Channel_Id = item['snippet']['channelId'],
                        Video_Id = item['id'],
                        Title = item['snippet']['title'],
                        Tags = item['snippet'].get('tags'),
                        Thumbnail = item['snippet']['thumbnails']['default']['url'],
                        Description = item['snippet']['description'],
                        Published_Date = item['snippet']['publishedAt'],
                        Duration = item['contentDetails']['duration'],
                        Views = item['statistics']['viewCount'],
                        Likes = item['statistics'].get('likeCount'),
                        Comments = item['statistics'].get('commentCount'),
                        Favorite_Count = item['statistics']['favoriteCount'],
                        Definition = item['contentDetails']['definition'],
                        Caption_Status = item['contentDetails']['caption']
                        )
            video_data.append(data)
    return video_data


#get comment information
def get_comment_info(videos_ids):
        Comment_Information = []
        try:
                for video_id in videos_ids:

                        request = youtube.commentThreads().list(
                                part = "snippet",
                                videoId = video_id,
                                maxResults = 50
                                )
                        response5 = request.execute()
                        
                        for item in response5["items"]:
                                comment_information = dict(
                                        Comment_Id = item["snippet"]["topLevelComment"]["id"],
                                        Video_Id = item["snippet"]["videoId"],
                                        Comment_Text = item["snippet"]["topLevelComment"]["snippet"]["textOriginal"],
                                        Comment_Author = item["snippet"]["topLevelComment"]["snippet"]["authorDisplayName"],
                                        Comment_Published = item["snippet"]["topLevelComment"]["snippet"]["publishedAt"])

                                Comment_Information.append(comment_information)
        except:
                pass
                
        return Comment_Information


#upload data to  mongo db
client= pymongo.MongoClient("mongodb://localhost:27017")

db= client["youtubedata"]

def channel_info(channel_id):
    ch_details=get_channel_data(channel_id)
    pl_details=get_playlist_info(channel_id)
    vi_data=channel_videoId(channel_id)
    vi_details=get_video_info(vi_data)
    com_details=get_comment_info(vi_data)

    coll1 = db["channel_details"]
    coll1.insert_one({"channel_information":ch_details,"playlist_information":pl_details,"video_information":vi_details,
                     "comment_information":com_details})
    
    return "upload completed successfully"

# connecting SQl

#Table creation for channels,playlists, videos, comments
def channels_table():
    mydb = mysql.connector.connect(host="localhost",
            user="root",
            password="",
            database= "youtube_data"
            )
    cursor = mydb.cursor()

    drop_query = ' ' 'drop table if exists channels' ' '
    cursor.execute(drop_query)
    mydb.commit()

    try:
        create_query = '''create table if not exists channels(Channel_Name varchar(100),
                        Channel_Id varchar(80) primary key, 
                        Subscription_Count bigint, 
                        Views bigint,
                        Total_Videos int,
                        Channel_Description text,
                        Playlist_Id varchar(50))'''
        cursor.execute(create_query)
        mydb.commit()
    except:
        print("Channels Table alredy created")

    ch_list=[]
    db= client["youtubedata"]
    coll1=db["channel_details"]
    for ch_data in coll1.find({},{"_id":0,"channel_information":1}):
        ch_list.append(ch_data["channel_information"])
        df  = pd.DataFrame(ch_list)
        
    for index, row in df.iterrows():
        insert_query= '''INSERT into channels(Channel_Name,
                                                    Channel_Id,
                                                    Subscription_Count,
                                                    Views,
                                                    Total_Videos,
                                                    Channel_Description,
                                                    Playlist_Id)
                                        VALUES(%s,%s,%s,%s,%s,%s,%s)'''
        
        values =(
                row['channelName'],
                row['channel_id'],
                row['subscribers'],
                row['views'],
                row['totalVideos'],
                row['channel_description'],
                row['playlistId'])
        try:                     
            cursor.execute(insert_query,values)
            mydb.commit()    
        except:
            print("Channels values are already inserted")

# creating playlist table

            
def playlists_table():

        mydb = mysql.connector.connect(host="localhost",
                user="root",
                password="",
                database= "youtube_data"
                )
        cursor = mydb.cursor()

        drop_query = ' ' 'drop table if exists playlists' ' '
        cursor.execute(drop_query)
        mydb.commit()

        create_query = '''create table if not exists playlists(Playlist_Id varchar(100) primary key,
                        Title varchar(80), 
                        ChannelId varchar(100), 
                        ChannelName varchar(100),
                        PublishedAt timestamp,
                        VideoCount int)'''

        cursor.execute(create_query)
        mydb.commit()

        pl_list=[]
        db= client["youtubedata"]
        coll1=db["channel_details"]
        for pl_data in coll1.find({},{"_id":0,"playlist_information":1}):
           for i in range (len(pl_data["playlist_information"])):
            pl_list.append(pl_data["playlist_information"][i])
            df1=pd.DataFrame(pl_list)


        for index , row in df1.iterrows():
            insert_query = '''INSERT into playlists(Playlist_Id,
                                                Title,
                                                ChannelId,
                                                ChannelName,
                                                PublishedAt,
                                                VideoCount)
                                        VALUES(%s,%s,%s,%s,%s,%s)'''           
        values =(
                        row['PlaylistId'],
                        row['Title'],
                        row['ChannelId'],
                        row['ChannelName'],
                        row['PublishedAt'],
                        row['VideoCount'])
                
                
        cursor.execute(insert_query,values)
        mydb.commit() 

#videos data table

def videos_table():
    mydb = mysql.connector.connect(host="localhost",
            user="root",
            password="",
            database= "youtube_data"
            )
    cursor = mydb.cursor()

    drop_query = "drop table if exists videos"
    cursor.execute(drop_query)
    mydb.commit()

    create_query = '''create table if not exists videos(Channel_Name varchar(150),
                            Channel_Id varchar(150),
                            Video_Id varchar(50)primary key,
                            Title varchar(150),
                            Tags text,
                            Thumbnail varchar(200),
                            Description text,
                            Published_Date timestamp,
                            Duration datetime,
                            Views bigint,
                            Likes bigint,
                            Comments int,
                            Favorite_Count int,
                            Definition varchar(10),
                            Caption_Status varchar(50)
                            )''' 

    cursor.execute(create_query)
    mydb.commit()


    vi_list=[]
    db= client["youtubedata"]
    coll1=db["channel_details"]
    for vi_data in coll1.find({},{"_id":0,"video_information":1}):
        for i in range (len(vi_data["video_information"])):
            vi_list.append(vi_data["video_information"][i])
            df2 = pd.DataFrame(vi_list)

    for index, row in df2.iterrows():
        # Flatten any nested structures (e.g., lists)
        flatten_row = {k: v[0] if isinstance(v, list) else v for k, v in row.items()}

        insert_query = '''INSERT INTO videos (
                        Channel_Name,
                        Channel_Id,
                        Video_Id,
                        Title,
                        Tags,
                        Thumbnail,
                        Description,
                        Published_Date,
                        Duration,
                        Views,
                        Likes,
                        Comments,
                        Favorite_Count,
                        Definition,
                        Caption_Status
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)'''

        values = (
            flatten_row['Channel_Name'],
            flatten_row['Channel_Id'],
            flatten_row['Video_Id'],
            flatten_row['Title'],
            flatten_row['Tags'],
            flatten_row['Thumbnail'],
            flatten_row['Description'],
            flatten_row['Published_Date'],
            flatten_row['Duration'],
            flatten_row['Views'],
            flatten_row['Likes'],
            flatten_row['Comments'],
            flatten_row['Favorite_Count'],
            flatten_row['Definition'],
            flatten_row['Caption_Status']
        )

        cursor.execute(insert_query, values)

    mydb.commit()

    #comments table

def comments_table():
      

    mydb = mysql.connector.connect(host="localhost",
            user="root",
            password="",
            database= "youtube_data"
            )
    cursor = mydb.cursor()


    drop_query = "drop table if exists comments"
    cursor.execute(drop_query)
    mydb.commit()

    try:
        create_query = '''CREATE TABLE if not exists comments(Comment_Id varchar(100) primary key,
                        Video_Id varchar(80),
                        Comment_Text text, 
                        Comment_Author varchar(150),
                        Comment_Published timestamp)'''
        cursor.execute(create_query)
        mydb.commit()
        
    except:
        st.write("Commentsp Table already created")

    com_list = []
    db = client["youtubedata"]
    coll1 = db["channel_details"]
    for com_data in coll1.find({},{"_id":0,"comment_information":1}):
        for i in range(len(com_data["comment_information"])):
            com_list.append(com_data["comment_information"][i])
    df3 = pd.DataFrame(com_list)

    for index, row in df3.iterrows():
            insert_query = '''
                INSERT INTO comments (Comment_Id,
                                        Video_Id ,
                                        Comment_Text,
                                        Comment_Author,
                                        Comment_Published)
                VALUES (%s, %s, %s, %s, %s)

            '''
            values = (
                row['Comment_Id'],
                row['Video_Id'],
                row['Comment_Text'],
                row['Comment_Author'],
                row['Comment_Published']
            )
            try:
                cursor.execute(insert_query,values)
                mydb.commit()
            except:
                st.write("This comments are already exist in comments table")



def tables():
    channels_table()
    playlists_table()
    videos_table()
    comments_table()
    return "Tables Created successfully"

    
def show_channels_table():
    ch_list=[]
    db= client["youtubedata"]
    coll1=db["channel_details"]
    for ch_data in coll1.find({},{"_id":0,"channel_information":1}):
        ch_list.append(ch_data["channel_information"])
    channels_table = st.dataframe(ch_list)
    return channels_table

def show_playlists_table():
        pl_list=[]
        db= client["youtubedata"]
        coll1=db["channel_details"]
        for pl_data in coll1.find({},{"_id":0,"playlist_information":1}):
           for i in range (len(pl_data["playlist_information"])):
            pl_list.append(pl_data["playlist_information"][i])
        playlists_table = st.dataframe(pl_list)
        return playlists_table

def show_videos_table():
    vi_list=[]
    db= client["youtubedata"]
    coll1=db["channel_details"]
    for vi_data in coll1.find({},{"_id":0,"video_information":1}):
        for i in range (len(vi_data["video_information"])):
            vi_list.append(vi_data["video_information"][i])
    videos_table = st.dataframe(vi_list)
    return videos_table

def show_comments_table():
    com_list = []
    db = client["youtubedata"]
    coll1 = db["channel_details"]
    for com_data in coll1.find({},{"_id":0,"comment_information":1}):
        for i in range(len(com_data["comment_information"])):
            com_list.append(com_data["comment_information"][i])
    comments_table = st.dataframe(com_list)
    return comments_table


#streamlit part
st.title(":red[YOUTUBE DATA HARVESTING AND WAREHOUSING]")
with st.sidebar:
    st.title(":blue[YOUTUBE DATA HARVESTING AND WAREHOUSING]")
    st.header("SKILL TAKE AWAY")
    st.caption('Python scripting')
    st.caption("Data Collection")
    st.caption("MongoDB")
    st.caption("API Integration")
    st.caption(" Data Managment using MongoDB and SQL")

channel_id = st.text_input("Enter the Channel id")
channels = channel_id.split(',')
channels = [ch.strip() for ch in channels if ch]

if st.button("Collect and Store data"):
    for channel in channels:
        ch_ids = []
        db = client["youtubedata"]
        coll1 = db["channel_details"]
        for ch_data in coll1.find({},{"_id":0,"channel_information":1}):
            ch_ids.append(ch_data["channel_information"]["channel_id"])
        if channel in ch_ids:
            st.success("Channel details of the given channel id: " + channel + " already exists")
        else:
            output = channel_info(channel)
            st.success(output)

if st.button("Migrate to SQL"):
    display =tables()
    st.success(display)
    
show_table = st.radio("SELECT THE TABLE FOR VIEW",(":green[channels]",":orange[playlists]",":red[videos]",":blue[comments]"))

if show_table == ":green[channels]":
    show_channels_table()
elif show_table == ":orange[playlists]":
    show_playlists_table()
elif show_table ==":red[videos]":
    show_videos_table()
elif show_table == ":blue[comments]":
    show_comments_table()

#SQL connection

mydb = mysql.connector.connect(host="localhost",
        user="root",
        password="",
        database= "youtube_data"
        )
cursor = mydb.cursor()

    
question = st.selectbox(
    'Please Select Your Question',
    ('1. All the videos and the Channel Name',
     '2. Channels with most number of videos',
     '3. 10 most viewed videos',
     '4. Comments in each video',
     '5. Videos with highest likes',
     '6. likes of all videos',
     '7. views of each channel',
     '8. videos published in the year 2022',
     '9. average duration of all videos in each channel',
     '10. videos with highest number of comments'))

     
if question == '1. All the videos and the Channel Name':
    query1 = "select Title as videos, Channel_Name as ChannelName from videos;"
    cursor.execute(query1)
    # mydb.commit()
    t1=cursor.fetchall()
    df5=(pd.DataFrame(t1, columns=["Video Title","Channel Name"]))
    st.write(df5)

elif question == '2. Channels with most number of videos':
    query2 = "select Channel_Name as ChannelName,Total_Videos as NO_Videos from channels order by Total_Videos desc;"
    cursor.execute(query2)
    # mydb.commit()
    t2=cursor.fetchall()
    st.write(pd.DataFrame(t2, columns=["Channel Name","No Of Videos"]))

elif question == '3. 10 most viewed videos':
    query3 = '''select Views as views , Channel_Name as ChannelName,Title as VideoTitle from videos 
                        where Views is not null order by Views desc limit 10;'''
    cursor.execute(query3)
    # mydb.commit()
    t3 = cursor.fetchall()
    st.write(pd.DataFrame(t3, columns = ["views","channel Name","video title"]))

elif question == '4. Comments in each video':
    query4 = "select Comments as No_comments ,Title as VideoTitle from videos where Comments is not null;"
    cursor.execute(query4)
    # mydb.commit()
    t4=cursor.fetchall()
    st.write(pd.DataFrame(t4, columns=["No Of Comments", "Video Title"]))

elif question == '5. Videos with highest likes':
    query5 = '''select Title as VideoTitle, Channel_Name as ChannelName, Likes as LikesCount from videos 
                       where Likes is not null order by Likes desc;'''
    cursor.execute(query5)
    # mydb.commit()
    t5 = cursor.fetchall()
    st.write(pd.DataFrame(t5, columns=["video Title","channel Name","like count"]))

elif question == '6. likes of all videos':
    query6 = '''select Likes as likeCount,Title as VideoTitle from videos;'''
    cursor.execute(query6)
    # mydb.commit()
    t6 = cursor.fetchall()
    st.write(pd.DataFrame(t6, columns=["like count","video title"]))

elif question == '7. views of each channel':
    query7 = "select Channel_Name as ChannelName, Views as Channelviews from channels;"
    cursor.execute(query7)
    # mydb.commit()
    t7=cursor.fetchall()
    st.write(pd.DataFrame(t7, columns=["channel name","total views"]))

elif question == '8. videos published in the year 2022':
    query8 = '''select Title as Video_Title, Published_Date as VideoRelease, Channel_Name as ChannelName from videos 
                where extract(year from Published_Date) = 2022;'''
    cursor.execute(query8)
    # mydb.commit()
    t8=cursor.fetchall()
    st.write(pd.DataFrame(t8,columns=["Name", "Video Publised On", "ChannelName"]))

elif question == '9. average duration of all videos in each channel':
    query9 =  "SELECT Channel_Name as ChannelName, AVG(Duration) AS average_duration FROM videos GROUP BY Channel_Name;"
    cursor.execute(query9)
    # mydb.commit()
    t9=cursor.fetchall()
    t9 = pd.DataFrame(t9, columns=['ChannelTitle', 'Average Duration'])
    T9=[]
    for index, row in t9.iterrows():
        channel_title = row['ChannelTitle']
        average_duration = row['Average Duration']
        average_duration_str = str(average_duration)
        T9.append({"Channel Title": channel_title ,  "Average Duration": average_duration_str})
    st.write(pd.DataFrame(T9))

elif question == '10. videos with highest number of comments':
    query10 = '''select Title as VideoTitle, Channel_Name as ChannelName, Comments as Comments from videos 
                       where Comments is not null order by Comments desc;'''
    cursor.execute(query10)
    # mydb.commit()
    t10=cursor.fetchall()
    st.write(pd.DataFrame(t10, columns=['Video Title', 'Channel Name', 'NO Of Comments']))
