import pymysql
import json
import os

try:
    conn = pymysql.connect(
        host="127.0.0.1",
        port=36301,
        user="root",
        password="alwaysup@888",
        database="alwaysup"
    )
    
    definition = {
        "id": "post_market_audit",
        "name": "Post-Market Data Quality Audit 4.0",
        "steps": [
            {
                "id": "calculate_quality",
                "task_id": "calculate_data_quality",
                "type": "docker",
                "params": {
                    "date": "{{target_date}}"
                }
            },
            {
                "id": "audit_decision",
                "task_id": "ai_quality_gatekeeper",
                "type": "docker",
                "depends_on": ["calculate_quality"],
                "params": {
                    "quality_report": "{{calculate_quality.output}}"
                }
            },
            {
                "id": "sync_tick",
                "task_id": "repair_tick",
                "type": "docker",
                "depends_on": ["audit_decision"],
                "params": {
                    "date": "{{target_date}}",
                    "stock_codes": "{{audit_decision.output.confirmed_bad_codes}}"
                }
            },
            {
                "id": "supplement_stock",
                "task_id": "stock_data_supplement",
                "type": "docker",
                "depends_on": ["audit_decision"],
                "params": {
                    "date": "{{target_date}}",
                    "stocks": "{{audit_decision.output.confirmed_bad_codes}}"
                }
            }
        ]
    }

    with conn.cursor() as cursor:
        sql = "INSERT INTO workflow_definitions (id, name, definition) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE definition = %s"
        cursor.execute(sql, (definition['id'], definition['name'], json.dumps(definition), json.dumps(definition)))
        conn.commit()
        print(f"Successfully registered workflow: {definition['id']}")
            
except Exception as e:
    print(f"Error: {e}")
finally:
    if 'conn' in locals() and conn:
        conn.close()
