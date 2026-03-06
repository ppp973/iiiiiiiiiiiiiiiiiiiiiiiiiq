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
                    # Get course details
                    course_url = f"https://backend.studyiq.net/app-content-ws/v1/course/getDetails?courseId={batch_id}&languageId="
                    master3 = await fetch_get(course_url, headers=headers)
                    
                    if not master3 or not master3.get('data'):
                        await progress_msg.edit(f"**❌ No data for batch {batch_id}**")
                        continue
                    
                    bname = master3.get("courseTitle", "Unknown")
                    all_urls = []
                    processed = 0
                    total = len(master3['data'])
                    
                    # Process content
                    for item in master3['data']:
                        t_id = str(item.get("contentId"))
                        if not t_id:
                            continue
                            
                        topicname = item.get('name', 'Unknown')
                        processed += 1
                        
                        # Update progress
                        if processed % 3 == 0:
                            try:
                                await progress_msg.edit(f"**📥 Processing:** {processed}/{total} - {topicname[:30]}...")
                            except:
                                pass

                        # Get parent content
                        parent_url = f"https://backend.studyiq.net/app-content-ws/v1/course/getDetails?courseId={batch_id}&languageId=&parentId={t_id}"
                        parent_data = await fetch_get(parent_url, headers=headers)
                        
                        if not parent_data or not parent_data.get('data'):
                            continue
                            
                        # Process videos and notes
                        for sub_item in parent_data['data']:
                            # Videos
                            url = sub_item.get('videoUrl')
                            name = sub_item.get('name', 'Untitled')
                            if url:
                                if url.endswith('.mpd'):
                                    all_urls.append(f"[DRM][{topicname}] - {name}: {url}")
                                else:
                                    all_urls.append(f"[{topicname}] - {name}: {url}")
                            
                            # Notes
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
                                                        all_urls.append(f"[Notes][{topicname}] - {url_data['name']}: {url_data['url']}")
                                except Exception as e:
                                    # यहां except ब्लॉक सही से लगा है
                                    print(f"Note fetch error: {e}")
                    
                    if all_urls:
                        await progress_msg.edit(f"**✅ Found {len(all_urls)} links! Sending...**")
                        await login(app, m, all_urls, start_time, bname, batch_id, CHANNEL_ID)
                        await m.reply_text(f"**✅ Batch {batch_id} completed successfully!**")
                    else:
                        await progress_msg.edit(f"**⚠️ No URLs found for batch {batch_id}**")
                    
                    await progress_msg.delete()
                    
                except Exception as e:
                    # यह मुख्य except ब्लॉक है - एरर आने पर यही चलेगा
                    await progress_msg.edit(f"**❌ Error:** `{str(e)[:100]}`")
                    # यहां से एरर हैंडल हो जाएगा, और लूप अगले बैच के लिए जारी रहेगा
                    
    except Exception as e:
        error_text = f"**❌ Error:** `{str(e)[:200]}`"
        if status_msg:
            await status_msg.edit(error_text)
        else:
            await m.reply_text(error_text)
