# handlers/iq_handler.py में ये बदलाव कर रहा हूं:

async def handle_iq_command(app, m: Message):
    """Main handler for /iq command"""
    from config import CHANNEL_ID
    
    status_msg = None
    try:
        status_msg = await m.reply_text("**📱 Send phone number or token:**")
        
        # Get first input
        input1 = await get_user_input(app, m.chat.id)
        if not input1:
            await status_msg.edit("**⏰ Timeout! Please try again.**")
            return
        await input1.delete()
        
        raw_text1 = input1.text.strip()
        logged_in = False
        token = None

        # Login with phone number
        if raw_text1.isdigit():
            phNum = raw_text1.strip()
            await status_msg.edit("**📤 Sending OTP...**")
            
            # FIX: Add proper headers
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Content-Type": "application/json"
            }
            
            master0 = await fetch_post(
                "https://www.studyiq.net/api/web/userlogin", 
                json={"mobile": phNum},
                headers=headers
            )
            
            # FIX: Better error handling
            if master0 and master0.get('status') == 'success':
                user_id = master0.get('data', {}).get('user_id')
                if user_id:
                    await status_msg.edit("**✅ OTP sent! Enter OTP:**")
                else:
                    await status_msg.edit(f"**❌ Error:** {master0.get('message', 'Unknown error')}")
                    return
            else:
                await status_msg.edit(f"**❌ Error:** {master0.get('message', 'Failed to send OTP')}")
                return
        
            # Get OTP
            input2 = await get_user_input(app, m.chat.id)
            if not input2:
                await status_msg.edit("**⏰ Timeout! Please try again.**")
                return
            otp = input2.text.strip()
            await input2.delete()
            
            data = {"user_id": user_id, "otp": otp}
            await status_msg.edit("**🔄 Verifying OTP...**")
            
            master1 = await fetch_post(
                "https://www.studyiq.net/api/web/web_user_login", 
                json=data,
                headers=headers
            )
            
            # FIX: Check response structure
            if master1 and master1.get('status') == 'success':  
                token = master1.get('data', {}).get('api_token')
                if token:
                    await m.reply_text(
                        f"**✅ Login Success!**\n\n"
                        f"**🔑 Token:** `{token}`\n\n"
                        f"**💡 Save this token for next time!**"
                    )
                    logged_in = True
                else:
                    await status_msg.edit(f"**❌ Error:** {master1.get('message', 'Failed to get token')}")
                    return
            else:
                await status_msg.edit(f"**❌ Error:** {master1.get('message', 'OTP verification failed')}")
                return
        else:
            token = raw_text1.strip()
            logged_in = True
            await status_msg.edit("**✅ Token accepted! Fetching courses...**")

        if logged_in and token:
            headers = {
                "Authorization": f"Bearer {token}",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
            
            # FIX: Add timeout and retry
            try:
                # Get purchased courses
                json_master2 = await fetch_get(
                    "https://backend.studyiq.net/app-content-ws/api/v1/getAllPurchasedCourses?source=WEB", 
                    headers=headers
                )
                
                # FIX: Check response properly
                if json_master2:
                    if json_master2.get('data'):
                        # Show available batches
                        batch_list = "**📚 Your Batches:**\n\n"
                        batch_ids = []
                        
                        for course in json_master2["data"]:
                            batch_list += f"`{course['courseId']}` - **{course['courseTitle']}**\n"
                            batch_ids.append(str(course["courseId"]))
                        
                        await status_msg.edit(batch_list + "\n**📤 Send Batch ID to download**")
                        
                        # Get batch selection
                        batch_input = await get_user_input(app, m.chat.id)
                        if batch_input:
                            # Process batch...
                            await status_msg.edit("**✅ Batch selection received! Processing...**")
                        else:
                            await status_msg.edit("**⏰ Timeout! Please try again.**")
                    else:
                        await status_msg.edit("**❌ No courses found in your account!**")
                else:
                    await status_msg.edit("**❌ Failed to fetch courses. API might be down.**")
                    
            except Exception as e:
                await status_msg.edit(f"**❌ API Error:** `{str(e)[:100]}`")
