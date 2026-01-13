/**
 * Twitter/X Scraper using @the-convocation/twitter-scraper
 * Uses cookies from logged-in session
 * 
 * Built by Friday
 */

import { Scraper } from '@the-convocation/twitter-scraper';
import * as fs from 'fs';

// User's cookies
const AUTH_TOKEN = '598847410fe3cef2e7e8edc56d5ee4365ae7355a';
const CT0 = 'b72143b89ae2beb13c3b73af8e1a262bcf25ab0b2f7baf881e662a52bdda9cc19a87c322f77b26f59859a00b0316aa14823e1b6c9c87f0020be29f7da00fa22006696767bbfca73c30dc4fcbc0a17443';

async function main() {
    const args = process.argv.slice(2);
    let keyword = 'indonesia';
    let count = 20;

    for (let i = 0; i < args.length; i++) {
        if (args[i] === '-k') keyword = args[++i];
        if (args[i] === '-c') count = parseInt(args[++i]) || 20;
    }

    console.log('🐦 Twitter/X Scraper (@the-convocation)\n');

    const scraper = new Scraper();

    // Set cookies
    console.log('🔑 Setting cookies...');

    const cookies = [
        `auth_token=${AUTH_TOKEN}; Domain=.twitter.com; Path=/; Secure; HttpOnly`,
        `ct0=${CT0}; Domain=.twitter.com; Path=/; Secure`
    ];

    await scraper.setCookies(cookies);

    // Check if logged in
    const isLoggedIn = await scraper.isLoggedIn();
    console.log(`   Logged in: ${isLoggedIn}`);

    if (!isLoggedIn) {
        console.log('\n⚠️ Not logged in. Trying login with credentials...');
        try {
            await scraper.login('feiscrap', '@Fairnanda049#');
            console.log('✅ Login successful!');
        } catch (e) {
            console.log(`❌ Login failed: ${e.message}`);
            console.log('\n💡 Cookies might be expired. Please get fresh cookies from browser.');
            return;
        }
    }

    console.log(`\n🔍 Searching for: '${keyword}'`);
    console.log(`   Target: ${count} tweets\n`);

    const tweets = [];

    try {
        // Search tweets
        const searchResults = scraper.searchTweets(keyword, count, 0);

        for await (const tweet of searchResults) {
            tweets.push({
                id: tweet.id,
                text: tweet.text,
                created_at: tweet.timeParsed,
                language: tweet.lang,
                like_count: tweet.likes || 0,
                retweet_count: tweet.retweets || 0,
                reply_count: tweet.replies || 0,
                views: tweet.views || 0,
                user: {
                    username: tweet.username,
                    display_name: tweet.name,
                }
            });

            if (tweets.length % 10 === 0) {
                console.log(`   Progress: ${tweets.length} tweets...`);
            }

            if (tweets.length >= count) break;
        }

        console.log(`\n✅ Fetched ${tweets.length} tweets`);

        // Export
        if (tweets.length > 0) {
            const filename = `tweets_${keyword.replace(/\s+/g, '_').substring(0, 20)}.json`;
            fs.writeFileSync(filename, JSON.stringify(tweets, null, 2), 'utf-8');
            console.log(`📁 Exported to ${filename}`);

            // Summary
            console.log('\n📊 Summary:');
            const totalLikes = tweets.reduce((sum, t) => sum + (t.like_count || 0), 0);
            console.log(`   Total Likes: ${totalLikes.toLocaleString()}`);

            if (tweets.length > 0) {
                const top = tweets.reduce((max, t) => (t.like_count || 0) > (max.like_count || 0) ? t : max);
                console.log(`   🔥 Top Tweet: @${top.user?.username}: "${(top.text || '').substring(0, 50)}..."`);
            }
        }

    } catch (error) {
        console.error(`\n❌ Error: ${error.message}`);
    }

    console.log('\n✨ Done!');
}

main().catch(console.error);
