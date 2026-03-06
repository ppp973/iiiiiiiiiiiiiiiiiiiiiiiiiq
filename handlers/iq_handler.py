import os
import re
import json
import datetime
import logging
import asyncio
import pytz
import aiofiles
import aiohttp
from pyrogram.types import Message
from pyrogram import filters

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
API_BASE_URL = "https://api.studyiq.net/v1"  # Updated API endpoint
WEB_BASE_URL = "https://www.studyiq.net"

async def fetch_post(url, json=None, headers=None):
    """Async POST request with debugging"""
    logger.info(f"📤 POST Request to: {url}")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=json, headers=headers, timeout=30) as response:
                response_text = await response.text()
                logger.info(f"📥 Response Status: {response.status}")
                
                if response.status == 200:
                    try:
                        return json.loads(response_text)
                    except:
                        return {"status": "success", "data": response_text}
                else:
                    logger.error(f"❌ HTTP {response.status}: {response_text[:200]}")
                    return {"error": f"HTTP {response.status}", "message": response_text[:200]}
        except asyncio.TimeoutError:
            logger.error("❌ Request timeout")
            return {"error": "timeout", "message": "Request timed out"}
        except Exception as e:
            logger.error(f"❌ Request failed: {str(e)}")
            return {"error": str(e)}

async def fetch_get(url, headers=None):
    """Async GET request with debugging"""
    logger.info(f"📤 GET Request to: {url}")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers, timeout=30) as response:
                response_text = await response.text()
                logger.info(f"📥 Response Status: {response.status}")
                
                if response.status == 200:
                    try:
                        return json.loads(response_text)
                    except:
                        return {"status": "success", "data": response_text}
                else:
                    logger.error(f"❌ HTTP {response.status}: {response_text[:200]}")
                    return None
        except Exception as e:
            logger.error(f"❌ Request failed: {str(e)}")
            return None

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
    video_count = len(re.findall(r'\.(m3u8|mp4)', all_text))
    pdf_count = len(re.findall(r'\.pdf', all_text))
    drm_videos = len(re.findall(r'\.mpd', all_text))
    
    caption = (
        f"**🎓 STUDY IQ EXTRACTOR**\n\n"
        f"**📚 Batch Details:**\n"
        f"├ ID: `{batch_id}`\n"
        f"├ Name: {bname}\n"
        f"└ Total Links: {len(all_urls)}\n\n"
        f"**📊 Statistics:**\n"
        f"├ 🎥 Videos: {video_count}\n"
        f"├ 📄 PDFs: {pdf_count}\n"
        f"├ 🔒 DRM: {drm_videos}\n"
        f"└ ⏱️ Time: {int(minutes)}m {int(seconds)}s\n\n"
        f"**⚡ @sdfvghhghhbnm_bot**"
    )
    
    # Write to file
    async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
        await f.writelines([url + '\n' for url in all_urls])
    
    # Send to user
    await m.reply_document(
        document=file_path,
        caption=caption
    )
    
    # Send to log channel
    if log_channel:
        try:
            await app.send_document(
                log_channel, 
                file_path, 
                caption=f"**New Extraction:** {bname}\n**Batch ID:** {batch_id}"
            )
        except Exception as e:
            logger.error(f"Log channel error: {e}")
    
    # Clean up
    try:
        os.remove(file_path)
    except:
        pass

async def get_user_input(app, chat_id, timeout=300):
    """Helper function to get user input"""
    future = asyncio.Future()
    
    @app.on_message(filters.chat(chat_id) & filters.text & ~filters.command(["start", "help", "about", "iq"]))
    def handler(client, message):
        if not future.done():
            future.set_result(message)
            handler.stop()
    
    try:
        return await asyncio.wait_for(future, timeout)
    except asyncio.TimeoutError:
        return None
    finally:
        handler.stop()

async def handle_iq_command(app, m: Message):
    """Main handler for /iq command"""
    from config import CHANNEL_ID
    
    status_msg = None
    try:
        status_msg = await m.reply_text("**📱 Send your 10-digit phone number or saved token:**")
        
        # Get first input
        input1 = await get_user_input(app, m.chat.id)
        if not input1:
            await status_msg.edit("**⏰ Timeout! Please try again.**")
            return
        await input1.delete()
        
        raw_text1 = input1.text.strip()
        logged_in = False
        token = None
        user_id = None

        # Common headers for all requests
        common_headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Content-Type": "application/json",
            "Origin": WEB_BASE_URL,
            "Referer": f"{WEB_BASE_URL}/",
            "Connection": "keep-alive"
        }

        # Login with phone number
        if raw_text1.isdigit():
            phNum = raw_text1.strip()
            
            # Validate phone number
            if len(phNum) != 10:
                await status_msg.edit("**❌ Please enter a valid 10-digit phone number**")
                return
            
            await status_msg.edit("**📤 Sending OTP...**")
            
            # Try different endpoints for OTP
            endpoints = [
                f"{API_BASE_URL}/auth/login",
                f"{WEB_BASE_URL}/api/web/userlogin",
                f"{WEB_BASE_URL}/api/v1/auth/login"
            ]
            
            success = False
            for endpoint in endpoints:
                try:
                    result = await fetch_post(
                        endpoint,
                        json={"mobile": phNum, "country_code": "91"},  # Assuming India
                        headers=common_headers
                    )
                    
                    if result and result.get('status') == 'success' or result.get('data'):
                        user_id = result.get('data', {}).get('user_id') or result.get('user_id')
                        success = True
                        logger.info(f"✅ OTP sent via {endpoint}")
                        break
                except:
                    continue
            
            if not success:
                await status_msg.edit("**❌ Failed to send OTP. Please try again later.**")
                return
            
            await status_msg.edit("**✅ OTP sent! Enter the 6-digit OTP:**")
        
            # Get OTP
            input2 = await get_user_input(app, m.chat.id)
            if not input2:
                await status_msg.edit("**⏰ Timeout! Please try again.**")
                return
            otp = input2.text.strip()
            await input2.delete()
            
            if len(otp) != 6 or not otp.isdigit():
                await status_msg.edit("**❌ Please enter a valid 6-digit OTP**")
                return
            
            await status_msg.edit("**🔄 Verifying OTP...**")
            
            # Verify OTP
            verify_data = {
                "mobile": phNum,
                "otp": otp,
                "user_id": user_id
            }
            
            verify_endpoints = [
                f"{API_BASE_URL}/auth/verify",
                f"{WEB_BASE_URL}/api/web/web_user_login",
                f"{WEB_BASE_URL}/api/v1/auth/verify"
            ]
            
            success = False
            for endpoint in verify_endpoints:
                result = await fetch_post(endpoint, json=verify_data, headers=common_headers)
                
                if result:
                    token = (result.get('data', {}).get('api_token') or 
                            result.get('data', {}).get('token') or 
                            result.get('token'))
                    
                    if token:
                        success = True
                        logger.info(f"✅ Login success via {endpoint}")
                        break
            
            if success and token:
                await m.reply_text(
                    f"**✅ Login Successful!**\n\n"
                    f"**🔑 Your Token (SAVE THIS):**\n"
                    f"`{token}`\n\n"
                    f"**💡 Next time just send this token directly!**"
                )
                logged_in = True
            else:
                await status_msg.edit("**❌ OTP verification failed. Please try again.**")
                return
        else:
            token = raw_text1.strip()
            logged_in = True
            await status_msg.edit("**✅ Token accepted! Fetching your courses...**")

        if logged_in and token:
            # Headers for authenticated requests
            auth_headers = {
                **common_headers,
                "Authorization": f"Bearer {token}"
            }
            
            # Try different endpoints for courses
            courses_endpoints = [
                f"{API_BASE_URL}/user/courses",
                f"{WEB_BASE_URL}/api/v1/user/courses",
                "https://backend.studyiq.net/app-content-ws/api/v1/getAllPurchasedCourses?source=WEB",
                f"{WEB_BASE_URL}/api/web/user/courses"
            ]
            
            courses_data = None
            for endpoint in courses_endpoints:
                result = await fetch_get(endpoint, headers=auth_headers)
                if result and result.get('data'):
                    courses_data = result.get('data')
                    logger.info(f"✅ Courses fetched from {endpoint}")
                    break
            
            if not courses_data:
                await status_msg.edit("**❌ No courses found or API error. Please check your token.**")
                return

            # Show available batches
            batch_list = "**📚 Your Batches:**\n\n"
            batch_ids = []
            
            for course in courses_data:
                course_id = course.get('courseId') or course.get('id')
                course_title = course.get('courseTitle') or course.get('title') or course.get('name')
                
                if course_id and course_title:
                    batch_list += f"`{course_id}` - **{course_title}**\n"
                    batch_ids.append(str(course_id))

            if not batch_ids:
                await status_msg.edit("**❌ No batches found in your account!**")
                return

            batch_ids_str = '&'.join(batch_ids)
            
            await status_msg.edit(
                f"{batch_list}\n"
                f"**📤 Send Batch ID to download**\n"
                f"**💡 For multiple batches, use &**\n"
                f"**Example:** `{batch_ids[0] if batch_ids else ''}&{batch_ids[1] if len(batch_ids) > 1 else ''}`"
            )
            
            # Get batch selection
            batch_input = await get_user_input(app, m.chat.id)
            if not batch_input:
                await status_msg.edit("**⏰ Timeout! Please try again.**")
                return
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
                    # Try different endpoints for batch details
                    batch_endpoints = [
                        f"{API_BASE_URL}/course/{batch_id}",
                        f"{WEB_BASE_URL}/api/v1/course/{batch_id}",
                        f"https://backend.studyiq.net/app-content-ws/v1/course/getDetails?courseId={batch_id}"
                    ]
                    
                    batch_details = None
                    batch_name = "Unknown"
                    
                    for endpoint in batch_endpoints:
                        result = await fetch_get(endpoint, headers=auth_headers)
                        if result:
                            batch_details = result.get('data') or result
                            batch_name = (batch_details.get('courseTitle') or 
                                        batch_details.get('title') or 
                                        batch_details.get('name') or 
                                        f"Batch_{batch_id}")
                            break
                    
                    if not batch_details:
                        await progress_msg.edit(f"**❌ No data for batch {batch_id}**")
                        continue
                    
                    all_urls = []
                    processed = 0
                    
                    # Extract content based on response structure
                    content_items = []
                    if isinstance(batch_details, dict):
                        content_items = batch_details.get('modules', []) or batch_details.get('chapters', []) or batch_details.get('data', [])
                    
                    total_items = len(content_items) if content_items else 1
                    
                    if not content_items:
                        # Try to extract videos directly
                        videos = batch_details.get('videos', []) or batch_details.get('contents', [])
                        for video in videos:
                            url = video.get('videoUrl') or video.get('url')
                            name = video.get('name') or video.get('title') or 'Video'
                            if url:
                                all_urls.append(f"[Video] - {name}: {url}")
                    
                    for item in content_items:
                        processed += 1
                        topicname = item.get('name') or item.get('title') or f"Topic_{processed}"
                        
                        # Update progress
                        if processed % 3 == 0:
                            try:
                                await progress_msg.edit(f"**📥 Processing:** {processed}/{total_items} - {topicname[:30]}...")
                            except:
                                pass
                        
                        # Get videos
                        videos = item.get('videos', []) or item.get('contents', [])
                        for video in videos:
                            url = video.get('videoUrl') or video.get('url')
                            name = video.get('name') or video.get('title') or 'Untitled'
                            if url:
                                all_urls.append(f"[{topicname}] - {name}: {url}")
                        
                        # Get notes/PDFs
                        notes = item.get('notes', []) or item.get('pdfs', []) or item.get('attachments', [])
                        for note in notes:
                            url = note.get('url') or note.get('pdfUrl') or note.get('fileUrl')
                            name = note.get('name') or note.get('title') or 'Note'
                            if url and url.endswith('.pdf'):
                                all_urls.append(f"[Notes][{topicname}] - {name}: {url}")
                    
                    if all_urls:
                        await progress_msg.edit(f"**✅ Found {len(all_urls)} links! Sending file...**")
                        await login(app, m, all_urls, start_time, batch_name, batch_id, CHANNEL_ID)
                        await m.reply_text(f"**✅ Batch {batch_id} completed successfully!**")
                    else:
                        await progress_msg.edit(f"**⚠️ No URLs found for batch {batch_id}**")
                    
                    await progress_msg.delete()
                    
                except Exception as e:
                    logger.error(f"Batch processing error: {str(e)}")
                    await progress_msg.edit(f"**❌ Error:** `{str(e)[:100]}`")
                    
    except Exception as e:
        logger.error(f"Main handler error: {str(e)}")
        error_text = f"**❌ Error:** `{str(e)[:200]}`"
        if status_msg:
            await status_msg.edit(error_text)
        else:
            await m.reply_text(error_text)
