import pandas as pd
import math

# Load and normalize
df = pd.read_csv("packet_routes.csv")
df['source'] = df['source'].astype(str).str.strip('"').str.strip()
df['dest']   = df['dest'].astype(str).str.strip('"').str.strip()
df['time']   = df['time'].astype(float)

df['is_request'] = df['packet_type'] == 'NETWORK_REQUEST'
df['is_reply']   = df['packet_type'] == 'NETWORK_REPLY'

# Track active request blocks by (source,dest)
active_blocks = {}

# Store results
blocks = []

for _, row in df.iterrows():
    key = (row['source'], row['dest'])
    
    # Handle requests
    if row['is_request']:
        if key not in active_blocks:
            active_blocks[key] = {
                'first_request_time': row['time'],
                'request_source': row['source'],
                'request_dest': row['dest'],
                'reply_times': [],
                'direct_reply_time': None
            }

    # Handle replies
    elif row['is_reply']:
        # A reply matches a request if: request.source = reply.dest AND request.dest = reply.source
        matching_key = (row['dest'], row['source'])
        if matching_key in active_blocks:
            block = active_blocks[matching_key]
            t = row['time']
            block['reply_times'].append(t)
            
            # Track DIRECT reply time
            if str(row.get('path_type','')).upper() == 'DIRECT':
                block['direct_reply_time'] = t
                
                # Determine last intermediate reply
                if len(block['reply_times']) >= 2:
                    last_intermediate = block['reply_times'][-2]
                    used_fallback = False
                else:
                    last_intermediate = block['direct_reply_time']
                    used_fallback = True

                delta = block['direct_reply_time'] - block['first_request_time']

                blocks.append({
                    'request_source': block['request_source'],
                    'request_dest': block['request_dest'],
                    'first_request_time': block['first_request_time'],
                    'last_intermediate_reply_time': (None if used_fallback else block['reply_times'][-2]),
                    'direct_reply_time': block['direct_reply_time'],
                    'delta': delta,
                    'used_fallback_direct_as_intermediate': used_fallback,
                    'num_replies': len(block['reply_times'])
                })

                # Remove completed block
                del active_blocks[matching_key]

# Handle any remaining requests that never got a DIRECT reply
for block in active_blocks.values():
    blocks.append({
        'request_source': block['request_source'],
        'request_dest': block['request_dest'],
        'first_request_time': block['first_request_time'],
        'last_intermediate_reply_time': None,
        'direct_reply_time': None,
        'delta': None,
        'used_fallback_direct_as_intermediate': False,
        'num_replies': len(block['reply_times'])
    })

results = pd.DataFrame(blocks)

# Optional: replace missing last_intermediate_reply_time with None for clarity
results['last_intermediate_reply_time'] = results['last_intermediate_reply_time'].where(
    pd.notna(results['last_intermediate_reply_time']), None)

# Write to CSV
results.to_csv("network_service_delay_results.csv", index=False)

print(f"Results written to 'network_service_delay_results.csv'")
print(f"Total requests processed: {len(results)}")
print(f"Unique clusterheads: {results['request_source'].nunique()}")
