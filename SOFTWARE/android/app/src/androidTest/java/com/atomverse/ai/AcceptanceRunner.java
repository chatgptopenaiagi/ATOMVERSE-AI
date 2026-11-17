package com.atomverse.ai;

import android.app.*;
import android.os.*;
import android.content.*;
import android.view.*;
import org.json.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.*;

/** Runs against the signed release APK; no acceptance backdoor in the application. */
public class AcceptanceRunner extends Instrumentation {
    JSONObject checks = new JSONObject(); MainActivity activity;
    void check(String name,boolean result) throws Exception { checks.put(name,result); if(!result)throw new AssertionError(name); }
    @Override public void onCreate(Bundle args){super.onCreate(args);start();}
    String bridge(String name,Object... args) throws Exception {return activity.worker.submit(()->activity.core.callAttr(name,args).toString()).get(30,TimeUnit.SECONDS);}
    void ui(Runnable r){runOnMainSync(r);waitForIdleSync();}
    @Override public void onStart(){JSONObject report=new JSONObject();long started=SystemClock.elapsedRealtime();int result=Activity.RESULT_CANCELED;
        try{
            Intent launch=new Intent(getTargetContext(),MainActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            activity=(MainActivity)startActivitySync(launch);
            long deadline=SystemClock.elapsedRealtime()+60000;while(!activity.ready&&SystemClock.elapsedRealtime()<deadline)Thread.sleep(100);
            check("shared_python_core_started",activity.ready);waitForIdleSync();
            check("demo_label",activity.packet.optString("mode").contains("SYNTHETIC"));
            JSONArray demo=activity.packet.getJSONArray("events");check("demo_isolated",demo.length()==64&&demo.getJSONObject(0).getString("data_kind").equals("synthetic"));
            check("no_automatic_observation",!activity.live&&activity.samples==0);
            float yaw=activity.universe.yaw;int[] xy=new int[2];ui(()->activity.universe.getLocationOnScreen(xy));
            long now=SystemClock.uptimeMillis();sendPointerSync(MotionEvent.obtain(now,now,MotionEvent.ACTION_DOWN,xy[0]+100,xy[1]+100,0));
            sendPointerSync(MotionEvent.obtain(now,now+30,MotionEvent.ACTION_MOVE,xy[0]+180,xy[1]+125,0));
            sendPointerSync(MotionEvent.obtain(now,now+60,MotionEvent.ACTION_UP,xy[0]+180,xy[1]+125,0));waitForIdleSync();
            check("touch_rotation",activity.universe.yaw!=yaw);
            float zoom=activity.universe.zoom;
            ui(()->pinch(activity.universe));check("touch_pinch_zoom",activity.universe.zoom>zoom);
            ui(()->{activity.interval=1;activity.toggleLive();});
            deadline=SystemClock.elapsedRealtime()+30000;while(activity.samples<4&&SystemClock.elapsedRealtime()<deadline)Thread.sleep(100);
            check("live_samples",activity.samples>=4&&activity.lastError.isEmpty());ui(()->activity.stopLive());
            JSONArray live=activity.packet.getJSONArray("events");boolean ram=false,cpu=false,gpu=false;
            for(int i=0;i<live.length();i++){JSONObject e=live.getJSONObject(i);JSONObject s=e.getJSONObject("scientific");
                if(e.getString("component").equals("memory")&&e.getJSONObject("metrics").has("used_pct"))ram=e.getJSONObject("metrics").getJSONObject("total_bytes").getLong("value")>0;
                if(e.getString("component").equals("cpu"))cpu=s.getJSONObject("metric_metadata").getJSONObject("utilization_pct").getString("classification").equals("DERIVED");
                if(e.getString("component").equals("gpu"))gpu=s.getString("classification").equals("UNAVAILABLE")&&e.getJSONObject("metrics").length()==0;
            }
            check("actual_device_ram",ram);check("app_scoped_derived_cpu",cpu);check("unsupported_gpu_is_unavailable",gpu);
            check("sqlite_integrity",bridge("integrity").equals("ok"));
            String exported=bridge("export_history");check("persisted_live_history",new JSONObject(exported).getJSONArray("events").length()>=20);
            File dir=getTargetContext().getExternalFilesDir("verification");dir.mkdirs();write(new File(dir,"android-export.json"),exported);
            File saved=new File(dir,"document-export.json");
            ui(()->activity.onActivityResult(11,Activity.RESULT_OK,new Intent().setData(android.net.Uri.fromFile(saved))));
            activity.worker.submit(()->true).get(30,TimeUnit.SECONDS);
            check("document_export_path",saved.length()>0&&activity.lastError.isEmpty());
            String fixture;try(InputStream in=getContext().getAssets().open("desktop-history.json")){fixture=MainActivity.readBounded(in);}
            JSONObject imported=new JSONObject(bridge("import_history",fixture));check("desktop_history_import",imported.getJSONArray("events").length()>=5);
            String roundtrip=bridge("export_history");write(new File(dir,"roundtrip-export.json"),roundtrip);
            JSONArray original=new JSONObject(fixture).getJSONArray("events"),round=new JSONObject(roundtrip).getJSONArray("events");
            boolean preserved=true;for(int i=0;i<original.length();i++){String id=original.getJSONObject(i).getString("event_id");boolean found=false;for(int j=0;j<round.length();j++)if(round.getJSONObject(j).getString("event_id").equals(id))found=true;preserved&=found;}
            check("imported_event_ids_preserved",preserved);
            boolean malformed=false;try{bridge("import_history","{\"format\":\"atomverse-export/1\",\"events\":[{}]}");}catch(Exception e){malformed=true;}check("malformed_import_rejected",malformed);
            ui(()->activity.requestHistory(3));Thread.sleep(500);check("recorded_replay_label",activity.packet.optString("mode").contains("RECORDED"));check("timeline_seek",activity.packet.getJSONArray("events").length()==3);
            check("rendered_frames",activity.universe.frames>5);report.put("last_paint_ms",activity.universe.paintMs);report.put("frames",activity.universe.frames);report.put("samples",activity.samples);
            ui(()->{activity.interval=1;activity.toggleLive();});Thread.sleep(1200);ui(()->activity.finish());
            check("worker_clean_shutdown",activity.worker.awaitTermination(10,TimeUnit.SECONDS)&&!activity.live&&activity.closed);
            report.put("status","PASS");result=Activity.RESULT_OK;
        }catch(Throwable e){try{report.put("status","FAIL");report.put("error",e.toString());}catch(Exception ignored){}if(activity!=null)try{ui(()->activity.finish());}catch(Exception ignored){}}
        try{report.put("checks",checks);report.put("elapsed_ms",SystemClock.elapsedRealtime()-started);report.put("supported_abis",new JSONArray(java.util.Arrays.asList(Build.SUPPORTED_ABIS)));report.put("sdk",Build.VERSION.SDK_INT);
            File dir=getTargetContext().getExternalFilesDir("verification");dir.mkdirs();write(new File(dir,"acceptance.json"),report.toString(2));
        }catch(Exception ignored){}Bundle out=new Bundle();out.putString("atomverse_report",report.toString());finish(result,out);
    }
    static void write(File file,String text)throws IOException{try(FileOutputStream out=new FileOutputStream(file)){out.write(text.getBytes(StandardCharsets.UTF_8));}}
    static void pinch(View v){long t=SystemClock.uptimeMillis();MotionEvent.PointerProperties[] p=new MotionEvent.PointerProperties[2];MotionEvent.PointerCoords[] c=new MotionEvent.PointerCoords[2];
        for(int i=0;i<2;i++){p[i]=new MotionEvent.PointerProperties();p[i].id=i;p[i].toolType=MotionEvent.TOOL_TYPE_FINGER;c[i]=new MotionEvent.PointerCoords();c[i].y=150;c[i].pressure=1;c[i].size=1;}
        c[0].x=v.getWidth()*.3f;c[1].x=v.getWidth()*.7f;
        v.dispatchTouchEvent(MotionEvent.obtain(t,t,MotionEvent.ACTION_DOWN,1,p,c,0,0,1,1,0,0,0,0));
        v.dispatchTouchEvent(MotionEvent.obtain(t,t+10,MotionEvent.ACTION_POINTER_DOWN|(1<<8),2,p,c,0,0,1,1,0,0,0,0));
        c[0].x=v.getWidth()*.15f;c[1].x=v.getWidth()*.85f;v.dispatchTouchEvent(MotionEvent.obtain(t,t+50,MotionEvent.ACTION_MOVE,2,p,c,0,0,1,1,0,0,0,0));
        c[0].x=v.getWidth()*.1f;c[1].x=v.getWidth()*.9f;v.dispatchTouchEvent(MotionEvent.obtain(t,t+80,MotionEvent.ACTION_MOVE,2,p,c,0,0,1,1,0,0,0,0));
        v.dispatchTouchEvent(MotionEvent.obtain(t,t+100,MotionEvent.ACTION_POINTER_UP|(1<<8),2,p,c,0,0,1,1,0,0,0,0));
        v.dispatchTouchEvent(MotionEvent.obtain(t,t+110,MotionEvent.ACTION_UP,1,p,c,0,0,1,1,0,0,0,0));
    }
}
