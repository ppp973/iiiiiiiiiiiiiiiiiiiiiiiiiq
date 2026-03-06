import os
import re
import datetime
import pytz
import aiofiles
import aiohttp
from pyrogram.types import Message

async def fetch_post(url, json=None, headers=None):
    """Async POST request"""
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=json, headers=headers) as response:
            return await response.json()

async def fetch_get(url, headers=None):
    """Async GET request"""
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                return await response.json()
            return {}

async def sanitize_bname(bname, max_length=50):
    """Sanitize filename"""
    bname = re.sub(r'[\\/:*?"<>|\t\n\r]+', '', bname).strip()
    if len(bname) > max_length:
        bname = bname[:max_length]
    return bname

async def login(app, m, all_urls, start_time, bname, batch_id, log_channel):
    """Save and send the extracted URLs"""
    bname = await sanitize_bname(bname)
    file_path = f"downloads/{bname}_{batch_id}.txt"
    
    end_time = datetime.datetime.now()
    duration = end_time - start_time
    minutes, seconds = divmod(duration.total_seconds(), 60)
    
    all_text = "\n".join(all_urls)
    video_count = len(re.findall(r'\.(m3u8|mpd|mp4)', all_text))
    pdf_count = len(re.findall(r'\.pdf', all_text))
    
    # Count DRM videos (if any)
    drm_videos = len(re.findall(r'\.(mpd|videoid)', all_text))
    
    caption = (
        f"**🎓 STUDY IQ EXTRACTOR**\n\n"
        f"**📚 Batch Details:**\n"
        f"├ ID: `{batch_id}`\n"
        f"├ Name: {bname}\n"
        f"└ Total Items: {len(all_urls)}\n\n"
        f"**📊 Content Statistics:**\n"
        f"├ 🎥 Videos: {video_count}\n"
        f"├ 📄 PDFs: {pdf_count}\n"
        f"├ 🔒 DRM Videos: {drm_videos}\n"
        f"└ ⏱️ Time: {int(minutes)}m {int(seconds)}s\n\n"
        f"**⚡ Extracted by @Ayushxsdy_Bot**"
    )
    
    # Write to file
    async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
        await f.writelines([url + '\n' for url in all_urls])
    
    # Send to user
    await m.reply_document(
        document=file_path,
        caption=caption
    )
    
    # Send to log channel (if configured)
    if log_channel:
        try:
            await app.send_document(
                log_channel, 
                file_path, 
                caption=f"**New Extraction:** {bname}\n**Batch ID:** {batch_id}"
            )
        except Exception as e:
            print(f"⚠️ Log channel error: {e}")
    
    # Clean up file
    try:
        os.remove(file_path)
    except:
        pass

async def handle_iq_command(app, m: Message):
    """Main handler for /iq command"""
    from config import CHANNEL_ID
    
    status_msg = None
    try:
        status_msg = await m.reply_text("**📱 Please send your phone number (without country code) or saved token:**")
        input1: Message = await app.listen(chat_id=m.chat.id)
        await input1.delete()
        raw_text1 = input1.text.strip()
        logged_in = False
        token = None

        # Login with phone number
        if raw_text1.isdigit():
            phNum = raw_text1.strip()
            await status_msg.edit("**📤 Sending OTP request...**")
            
            # Request OTP
            master0 = await fetch_post("https://www.studyiq.net/api/web/userlogin", json={"mobile": phNum})
            
            if master0.get('data'):
                user_id = master0.get('data', {}).get('user_id')
                if user_id:
                    await status_msg.edit("**✅ OTP sent! Please enter the OTP:**")
                else:
                    await status_msg.edit(f"**❌ Error:** {master0.get('msg', 'Unknown error')}")
                    return
            else:
                await status_msg.edit(f"**❌ Error:** {master0.get('msg', 'Failed to send OTP')}")
                return
        
            # Get OTP from user
            input2 = await app.listen(chat_id=m.chat.id)
            raw_text2 = input2.text.strip()
            otp = raw_text2
            await input2.delete()
            
            # Verify OTP
            data = {
                "user_id": user_id,
                "otp": otp
            }

            await status_msg.edit("**🔄 Verifying OTP...**")
            master1 = await fetch_post("https://www.studyiq.net/api/web/web_user_login", json=data)
            
            if master1.get('data'):  
                token = master1.get('data', {}).get('api_token')
                if token:
                    await m.reply_text(
                        f"**✅ Login Successful!**\n\n"
                        f"**🔑 Your Access Token (SAVE THIS):**\n"
                        f"`{token}`\n\n"
                        f"**💡 Next time you can just send this token directly!**"
                    )
                    logged_in = True
                else:
                    await status_msg.edit(f"**❌ Error:** {master1.get('msg', 'Login failed')}")
                    return
            else:
                await status_msg.edit(f"**❌ Error:** {master1.get('msg', 'OTP verification failed')}")
                return
        else:
            token = raw_text1.strip()
            logged_in = True
            await status_msg.edit("**✅ Token accepted! Fetching your courses...**")

        if logged_in and token:
            headers = {
                "Authorization": f"Bearer {token}",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json"
            }
            
            # Get purchased courses
            await status_msg.edit("**📚 Fetching your purchased courses...**")
            json_master2 = await fetch_get(
                "https://backend.studyiq.net/app-content-ws/api/v1/getAllPurchasedCourses?source=WEB", 
                headers=headers
            )
            
            if not json_master2 or not json_master2.get('data'):
                await status_msg.edit("**❌ No purchased courses found!**")
                return

            # Display available batches
            batch_list = "**📚 Your Batches:**\n\n"
            batch_ids = []
            
            for idx, course in enumerate(json_master2["data"], 1):
                batch_list += f"{idx}. `{course['courseId']}` - **{course['courseTitle']}**\n"
                batch_ids.append(str(course["courseId"]))

            batch_ids_str = '&'.join(batch_ids)
            
            await status_msg.edit(
                f"{batch_list}\n"
                f"**📤 Send the Batch ID to download**\n"
                f"**💡 For multiple batches, use & (e.g., `{batch_ids[0] if batch_ids else ''}&{batch_ids[1] if len(batch_ids)>1 else ''}`)**"
            )
            
            # Get batch selection
            batch_input = await app.listen(chat_id=m.chat.id)
            await batch_input.delete()
            await status_msg.delete()
            
            # Parse batch IDs
            if "&" in batch_input.text:
                selected_batches = batch_input.text.split('&')
            else:
                selected_batches = [batch_input.text]

            # Process each batch
            for batch_id in selected_batches:
                batch_id = batch_id.strip()
                if not batch_id:
                    continue
                    
                start_time = datetime.datetime.now()
                progress_msg = await m.reply_text(f"**🔄 Processing batch {batch_id}...**")

                try:
                    # Get course details
                    course_url = f"https://backend.studyiq.net/app-content-ws/v1/course/getDetails?courseId={batch_id}&languageId="
                    master3 = await fetch_get(course_url, headers=headers)
                    
                    if not master3 or not master3.get('data'):
                        await progress_msg.edit(f"**❌ No data found for batch {batch_id}**")
                        continue
                    
                    bname = master3.get("courseTitle", "Unknown Batch").replace(' || ', '').replace('|', '')
                    all_urls = []
                    processed = 0
                    
                    # Get all content IDs
                    content_items = master3['data']
                    
                    for item in content_items:
                        t_id = str(item.get("contentId"))
                        if not t_id:
                            continue
                            
                        topicname = item.get('name', 'Unknown Topic')
                        
                        # Update progress every 5 items
                        processed += 1
                        if processed % 5 == 0:
                            try:
                                await progress_msg.edit(f"**📥 Processing:** {topicname[:30]}... ({processed}/{len(content_items)})")
                            except:
                                pass

                        # Get parent content
                        parent_url = f"https://backend.studyiq.net/app-content-ws/v1/course/getDetails?courseId={batch_id}&languageId=&parentId={t_id}"
                        parent_data = await fetch_get(parent_url, headers=headers)
                        
                        if not parent_data or not parent_data.get('data'):
                            continue
                            
                        # Process each video/PDF
                        for sub_item in parent_data['data']:
                            # Handle videos
                            url = sub_item.get('videoUrl')
                            name = sub_item.get('name', 'Untitled')
                            
                            if url:
                                cc = f"[{topicname}] - {name}: {url}"
                                all_urls.append(cc)
                            
                            # Handle notes/PDFs
                            contentIdy = sub_item.get('contentId')
                            if contentIdy:
                                try:
                                    lesson_url = f"https://backend.studyiq.net/app-content-ws/api/lesson/data?lesson_id={contentIdy}&courseId={batch_id}"
                                    response = await fetch_get(lesson_url, headers=headers)
                                    
                                    if response and response.get('options'):
                                        for option in response['options']:
                                            if option.get('urls'):
                                                for url_data in option['urls']:
                                                    if 'name' in url_data and 'url' in url_data:
                                                        name = url_data['name']
                                                        url = url_data['url']
                                                        cc = f"[Notes] - {name}: {url}"
                                                        all_urls.append(cc)
                                except Exception as e:
                                    print(f"⚠️ Error fetching lesson: {e}")
                    
                    if all_urls:
                        await progress_msg.edit(f"**✅ Found {len(all_urls)} links! Sending file...**")
                        await login(app, m, all_urls, start_time, bname, batch_id, CHANNEL_ID)
                    else:
                        await progress_msg.edit(f"**⚠️ No URLs found for batch {batch_id}**")
                    
                    await progress_msg.delete()
                    
                except Exception as e:
                    await progress_msg.edit(f"**❌ Error:** `{str(e)[:100]}`")
                    
    except Exception as e:
        error_text = f"**❌ Error:** `{str(e)[:200]}`"
        if status_msg:
            await status_msg.edit(error_text)
        else:
            await m.reply_text(error_text)
