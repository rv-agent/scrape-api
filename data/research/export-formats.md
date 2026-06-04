# Data Export Formats

## Supported Formats
| Format | Use Case | Streaming |
|--------|----------|-----------|
| JSON | API default, structured | Yes |
| CSV | Spreadsheet, data analysis | Yes |
| Excel | Business users | No (full generation) |

## JSON Export
```python
@app.get("/api/v1/jobs/{job_id}/export")
async def export_job(job_id: str, format: str = "json", key=Depends(get_api_key)):
    job = await get_job(job_id, key)
    
    if format == "json":
        return JSONResponse(content=job.result)
    elif format == "csv":
        return StreamingResponse(
            generate_csv(job.result),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={job_id}.csv"}
        )
    elif format == "xlsx":
        buffer = generate_excel(job.result)
        return StreamingResponse(
            buffer,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={job_id}.xlsx"}
        )
```

## CSV Streaming
```python
import csv, io

async def generate_csv(data):
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=data[0].keys())
    writer.writeheader()
    for row in data:
        writer.writerow(row)
        output.seek(0)
        yield output.read()
        output.truncate(0)
        output.seek(0)
```

## Large Dataset Handling
- Stream response (don't load all in memory)
- Chunk size: 8KB per write
- For batch exports: zip file with multiple CSVs
- Background generation for > 10K rows: generate, store, return download link

## Batch Export
```python
@app.get("/api/v1/batches/{batch_id}/export")
async def export_batch(batch_id: str, format: str = "zip", key=Depends(get_api_key)):
    jobs = await get_batch_jobs(batch_id, key)
    
    if format == "zip":
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as zf:
            for job in jobs:
                if job.result:
                    zf.writestr(f"{job.id}.json", json.dumps(job.result))
        buffer.seek(0)
        return StreamingResponse(buffer, media_type="application/zip")
```

## Limits per Tier
| Tier | Max Export Rows | Formats |
|------|----------------|---------|
| Free | 100 | JSON |
| Starter | 10,000 | JSON, CSV |
| Pro | 100,000 | JSON, CSV, Excel |
| Enterprise | Unlimited | All + Custom |
