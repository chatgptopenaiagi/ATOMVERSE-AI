package com.atomverse.ai;

import android.app.*;
import android.os.*;
import android.content.*;
import android.graphics.*;
import android.net.Uri;
import android.view.*;
import android.widget.*;
import com.chaquo.python.*;
import com.chaquo.python.android.AndroidPlatform;
import org.json.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.*;

/** Foreground-only observer. Android APIs feed the authoritative Python core. */
public class MainActivity extends Activity {
    final ScheduledThreadPoolExecutor worker = new ScheduledThreadPoolExecutor(1);
    PyObject core;
    ScheduledFuture<?> sampling;
    volatile boolean live = false, ready = false, closed = false;
    volatile int samples = 0, interval = 2, frameLimit = 30;
    volatile String lastError = "", lastExport = "";
    volatile JSONObject packet = new JSONObject();
    Universe universe;
    TextView badge, detail, stats;
    Button start;
    SeekBar timeline;
    long lastPublished = 0;
    int pending = 0, retentionRows=3000, retentionHours=24;
    String mode = "DEMO: SYNTHETIC DATA";

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        worker.setRemoveOnCancelPolicy(true);
        SharedPreferences prefs=getPreferences(MODE_PRIVATE);
        interval=prefs.getInt("interval",2); frameLimit=prefs.getInt("fps",30);
        retentionRows=prefs.getInt("rows",3000); retentionHours=prefs.getInt("hours",24);
        getWindow().setStatusBarColor(Color.rgb(9,16,30));
        LinearLayout root = new LinearLayout(this); root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(16,16,16,8); root.setBackgroundColor(Color.rgb(9,16,30)); setContentView(root);
        if(Build.VERSION.SDK_INT>=30)root.setOnApplyWindowInsetsListener((v,insets)->{
            android.graphics.Insets bars=insets.getInsets(WindowInsets.Type.systemBars());
            v.setPadding(16+bars.left,16+bars.top,16+bars.right,8+bars.bottom);return insets;
        });
        TextView title = text("⚛ ATOMVERSE AI", 24); title.setTextColor(Color.rgb(101,186,255)); root.addView(title);
        root.addView(text("INFORMATION BECOMES MOTION", 10));
        badge = text("Starting shared computational core…", 12); root.addView(badge);
        stats = text("Observation is off · no background service", 11); root.addView(stats);
        universe = new Universe(this); root.addView(universe, new LinearLayout.LayoutParams(-1,0,1));
        detail = text("Tap a particle for its source, metric, classification and evidence. Drag to rotate · pinch to zoom.", 11);
        root.addView(detail);
        timeline = new SeekBar(this); timeline.setMax(10000); timeline.setVisibility(View.GONE); root.addView(timeline);
        timeline.setOnSeekBarChangeListener(new SeekBar.OnSeekBarChangeListener() {
            public void onStartTrackingTouch(SeekBar s) {}
            public void onStopTrackingTouch(SeekBar s) { requestHistory(Math.max(1,s.getProgress())); }
            public void onProgressChanged(SeekBar s,int p,boolean user) {}
        });
        LinearLayout row = row(root);
        start = button(row,"Start live", v -> toggleLive());
        button(row,"Demo", v -> demo()); button(row,"Replay", v -> requestHistory(256));
        row = row(root);
        button(row,"Data", v -> inspectData()); button(row,"Import", v -> chooseImport());
        button(row,"Export", v -> chooseExport()); button(row,"Settings", v -> settings());
        worker.execute(() -> { try {
            if (!Python.isStarted()) Python.start(new AndroidPlatform(this));
            core = Python.getInstance().getModule("atomverse.mobile").get("Mobile").call(getFilesDir().getAbsolutePath());
            core.callAttr("settings",retentionRows,retentionHours);
            publish(core.callAttr("demo").toString()); ready = true;
        } catch (Throwable e) { error(e); } });
    }
    TextView text(String value,int size) { TextView t = new TextView(this); t.setText(value); t.setTextSize(size); t.setTextColor(Color.rgb(211,224,243)); return t; }
    LinearLayout row(LinearLayout root) { LinearLayout r = new LinearLayout(this); root.addView(r); return r; }
    Button button(LinearLayout row,String title,View.OnClickListener action) { Button b = new Button(this); b.setText(title); b.setTextSize(11); b.setPadding(1,1,1,1); b.setAllCaps(false); row.addView(b,new LinearLayout.LayoutParams(0,(int)(48*getResources().getDisplayMetrics().density),1)); b.setOnClickListener(action); return b; }
    void error(Throwable e) { lastError = e.getClass().getSimpleName()+": "+e.getMessage(); runOnUiThread(() -> { if (!closed) { badge.setText("ERROR · "+lastError); stopLive(); } }); }
    void enqueue(Runnable action) { if(closed||!ready)return; synchronized(this){if(pending>=2){badge.setText("Busy · wait for the current data operation");return;}pending++;}
        worker.execute(()->{try{action.run();}finally{synchronized(this){pending--;}}}); }
    void publish(String json) throws JSONException {
        JSONObject p = new JSONObject(json); packet = p;
        runOnUiThread(() -> { if (closed) return; mode = p.optString("mode"); badge.setText(mode.startsWith("LIVE")&&!live?"PAUSED · last recorded observations":mode);
            stats.setText("Stored: "+p.optInt("stored")+" · sample interval "+interval+"s · OBS blue / DER green / AI purple / SIM gold / N/A gray");
            universe.setPacket(p); timeline.setMax(Math.max(1,p.optInt("stored"))); lastPublished = SystemClock.elapsedRealtime();
        });
    }
    void toggleLive() {
        if (live) { stopLive(); return; }
        if (!ready || closed) return;
        live = true; universe.animate=true; universe.invalidate(); lastError = ""; timeline.setVisibility(View.GONE); start.setText("Pause live");
        sampling = worker.scheduleWithFixedDelay(() -> { if (!live || closed) return; try {
            publish(core.callAttr("sample", measurements().toString()).toString()); samples++;
        } catch(Throwable e) { error(e); } },0,interval,TimeUnit.SECONDS);
    }
    void stopLive() { live = false; if(universe!=null)universe.animate=false; if (sampling != null) sampling.cancel(false); if(start != null) start.setText("Start live"); if(badge != null && mode.startsWith("LIVE")) badge.setText("PAUSED · last recorded observations"); }
    JSONObject measurements() throws JSONException {
        JSONObject raw = new JSONObject();
        ActivityManager am = (ActivityManager)getSystemService(ACTIVITY_SERVICE);
        try { ActivityManager.MemoryInfo mi = new ActivityManager.MemoryInfo(); am.getMemoryInfo(mi);
            raw.put("ram",new JSONObject().put("total",mi.totalMem).put("available",mi.availMem)); } catch(Exception ignored) {}
        try { StatFs fs = new StatFs(getFilesDir().getAbsolutePath()); raw.put("storage",new JSONObject().put("total",fs.getTotalBytes()).put("available",fs.getAvailableBytes())); } catch(Exception ignored) {}
        raw.put("app_cpu_ms",android.os.Process.getElapsedCpuTime()); raw.put("elapsed_ms",SystemClock.elapsedRealtime());
        raw.put("logical_processors",Runtime.getRuntime().availableProcessors());
        try { Debug.MemoryInfo mi = new Debug.MemoryInfo(); Debug.getMemoryInfo(mi); raw.put("app_pss_bytes",mi.getTotalPss()*1024L); } catch(Exception ignored) {}
        return raw;
    }
    void demo() { stopLive(); universe.animate=true; timeline.setVisibility(View.GONE); enqueue(() -> { try { publish(core.callAttr("demo").toString()); } catch(Throwable e) { error(e); } }); }
    void requestHistory(int count) { stopLive(); timeline.setVisibility(View.VISIBLE); enqueue(() -> { try { publish(core.callAttr("history",count).toString()); } catch(Throwable e) { error(e); } }); }
    void inspectData() { JSONArray events = packet.optJSONArray("events"); if(events == null) return;
        String[] labels = new String[events.length()]; for(int i=0;i<labels.length;i++) { JSONObject e=events.optJSONObject(i); labels[i]=e.optString("component")+" · "+e.optString("source")+" · "+e.optString("timestamp_utc"); }
        new AlertDialog.Builder(this).setTitle("Scientific evidence · select an event").setItems(labels,(d,i)->inspect(events.optJSONObject(i))).setNegativeButton("Close",null).show(); }
    void inspect(JSONObject event) { if(event==null)return; TextView t=text("",12); t.setTextIsSelectable(true); t.setPadding(20,10,20,10); try { t.setText(event.toString(2)); } catch(Exception e) { t.setText(event.toString()); }
        ScrollView scroll=new ScrollView(this); scroll.addView(t); new AlertDialog.Builder(this).setTitle("Source event · exact measurements").setView(scroll).setPositiveButton("Close",null).show(); }
    void chooseImport() { stopLive(); Intent intent=new Intent(Intent.ACTION_OPEN_DOCUMENT); intent.setType("application/json"); intent.addCategory(Intent.CATEGORY_OPENABLE); startActivityForResult(intent,10); }
    void chooseExport() { if(!ready)return; Intent intent=new Intent(Intent.ACTION_CREATE_DOCUMENT); intent.setType("application/json"); intent.addCategory(Intent.CATEGORY_OPENABLE); intent.putExtra(Intent.EXTRA_TITLE,"atomverse-history.json"); startActivityForResult(intent,11); }
    @Override protected void onActivityResult(int request,int result,Intent data) { super.onActivityResult(request,result,data); if(result!=RESULT_OK||data==null||data.getData()==null||!ready)return; Uri uri=data.getData();
        enqueue(() -> { try {
            if(request==10) { try(InputStream in=getContentResolver().openInputStream(uri)) { publish(core.callAttr("import_history",readBounded(in)).toString()); } }
            if(request==11) { File staged=new File(getCacheDir(),"history-export.json"); core.callAttr("export_file",staged.getAbsolutePath());
                try(InputStream in=new FileInputStream(staged);OutputStream out=getContentResolver().openOutputStream(uri,"wt")) { byte[] buffer=new byte[8192];int n;while((n=in.read(buffer))!=-1)out.write(buffer,0,n); }finally{staged.delete();}
                runOnUiThread(()->badge.setText("Exported classified history · retained observations and imported evidence")); }
        } catch(Throwable e) { error(e); } }); }
    static String readBounded(InputStream in) throws IOException { ByteArrayOutputStream b=new ByteArrayOutputStream(); byte[] buf=new byte[8192]; int n; while((n=in.read(buf))!=-1) { if(b.size()+n>4*1024*1024)throw new IOException("Import exceeds 4 MiB"); b.write(buf,0,n); } return b.toString("UTF-8"); }
    void settings() { stopLive(); LinearLayout box=new LinearLayout(this); box.setPadding(24,8,24,8); box.setOrientation(LinearLayout.VERTICAL);
        box.addView(text("Sampling seconds (1–30)",14)); EditText seconds=new EditText(this); seconds.setInputType(2); seconds.setText(""+interval); box.addView(seconds);
        box.addView(text("Rolling history rows (100–10000); imported evidence is protected",14)); EditText rows=new EditText(this); rows.setInputType(2); rows.setText(""+retentionRows); box.addView(rows);
        box.addView(text("History hours (1–720)",14)); EditText hours=new EditText(this); hours.setInputType(2); hours.setText(""+retentionHours); box.addView(hours);
        box.addView(text("Rendering FPS (10–30)",14)); EditText fps=new EditText(this); fps.setInputType(2); fps.setText(""+frameLimit); box.addView(fps);
        Button licenses=new Button(this);licenses.setText("Runtime licenses");box.addView(licenses);licenses.setOnClickListener(v->{try{
            String content="";for(String name:new String[]{"PYTHON.txt","CHAQUOPY.txt"})try(InputStream in=getAssets().open(name)){content+=name+"\n"+readBounded(in)+"\n\n";}
            TextView label=text(content,12);label.setTextIsSelectable(true);ScrollView scroll=new ScrollView(this);scroll.addView(label);new AlertDialog.Builder(this).setTitle("Third-party runtime licenses").setView(scroll).setPositiveButton("Close",null).show();
        }catch(Throwable e){error(e);}});
        new AlertDialog.Builder(this).setTitle("Bounded foreground observation").setView(box).setNegativeButton("Cancel",null).setPositiveButton("Apply",(d,w)->{ try {
            int s=Integer.parseInt(seconds.getText().toString()),f=Integer.parseInt(fps.getText().toString()),r=Integer.parseInt(rows.getText().toString()),h=Integer.parseInt(hours.getText().toString());
            if(s<1||s>30||f<10||f>30||r<100||r>10000||h<1||h>720)throw new IllegalArgumentException("Settings out of bounds");
            interval=s; frameLimit=f;retentionRows=r;retentionHours=h;getPreferences(MODE_PRIVATE).edit().putInt("interval",s).putInt("fps",f).putInt("rows",r).putInt("hours",h).apply();enqueue(()->{try{core.callAttr("settings",r,h);}catch(Throwable e){error(e);}});
        }catch(Throwable e){error(e);} }).show(); }
    @Override protected void onPause() { super.onPause(); stopLive(); if(universe!=null)universe.animate=false; }
    @Override protected void onResume() { super.onResume(); if(universe!=null){universe.animate=true; universe.invalidate();} }
    @Override protected void onDestroy() { stopLive(); closed=true; universe.animate=false; worker.execute(()->{if(core!=null)core.callAttr("close");}); worker.shutdown(); super.onDestroy(); }

    class Universe extends View {
        Paint paint=new Paint(3); JSONArray objects=new JSONArray(),events=new JSONArray();
        float yaw=0.3f,tilt=0.45f,zoom=1,dx=0,dy=0,downX,downY,lastX,lastY;
        boolean animate=true; long frames=0; double paintMs=0;
        final String[] orbits={"cpu","gpu","memory","storage","ai","code","database","guardian"};
        final ScaleGestureDetector scale;
        Universe(Context c){super(c); scale=new ScaleGestureDetector(c,new ScaleGestureDetector.SimpleOnScaleGestureListener(){public boolean onScale(ScaleGestureDetector d){zoom=Math.max(.4f,Math.min(2.5f,zoom*d.getScaleFactor()));invalidate();return true;}});}
        void setPacket(JSONObject p){objects=p.optJSONArray("objects");events=p.optJSONArray("events");invalidate();}
        float[] position(int orbit,double phase){double a=phase+yaw;float radius=Math.min(getWidth(),getHeight())*(.12f+orbit*.038f)*zoom;return new float[]{getWidth()/2f+dx+(float)Math.cos(a)*radius,getHeight()/2f+dy+(float)Math.sin(a)*radius*(.3f+Math.abs(tilt))};}
        @Override protected void onDraw(Canvas c){long begin=System.nanoTime();super.onDraw(c);c.drawColor(Color.rgb(9,16,30));
            paint.setStyle(Paint.Style.STROKE);paint.setStrokeWidth(1);paint.setColor(Color.rgb(34,53,78));
            for(int i=0;i<8;i++){float[] a=position(i,0);float radius=Math.abs(a[0]-(getWidth()/2f+dx))/Math.max(.1f,(float)Math.abs(Math.cos(yaw)));float cx=getWidth()/2f+dx,cy=getHeight()/2f+dy;
                c.drawOval(cx-radius,cy-radius*(.3f+Math.abs(tilt)),cx+radius,cy+radius*(.3f+Math.abs(tilt)),paint);}
            paint.setStyle(Paint.Style.FILL);paint.setColor(Color.rgb(101,186,255));c.drawCircle(getWidth()/2f+dx,getHeight()/2f+dy,15*zoom,paint);
            paint.setTextSize(12*getResources().getDisplayMetrics().density);c.drawText("COMPUTATIONAL NUCLEUS",18,40,paint);
            if(objects!=null)for(int i=0;i<Math.min(256,objects.length());i++){JSONObject o=objects.optJSONObject(i);int orbit=orbitIndex(o.optString("orbit"));double energy=o.optDouble("energy");
                // Angular speed and radius use validated dimensionless visual energy, never fabricate a measurement.
                float[] p=position(orbit,o.optDouble("phase")+frames/(double)frameLimit*energy*.04);
                paint.setColor(Color.parseColor(o.optString("color","#8292ab")));c.drawCircle(p[0],p[1],(float)(3+energy*8)*zoom,paint);
                if(i<8){paint.setTextSize(10*getResources().getDisplayMetrics().density);c.drawText(o.optString("orbit").toUpperCase(),p[0]+10,p[1],paint);}}
            frames++;paintMs=(System.nanoTime()-begin)/1e6;if(animate)postInvalidateDelayed(1000/frameLimit);
        }
        int orbitIndex(String s){for(int i=0;i<orbits.length;i++)if(orbits[i].equals(s))return i;return 7;}
        @Override public boolean onTouchEvent(android.view.MotionEvent e){scale.onTouchEvent(e);float x=e.getX(),y=e.getY();
            if(e.getActionMasked()==MotionEvent.ACTION_DOWN){downX=lastX=x;downY=lastY=y;return true;}
            if(e.getActionMasked()==MotionEvent.ACTION_MOVE&&!scale.isInProgress()){if(e.getPointerCount()==2){dx+=(x-lastX);dy+=(y-lastY);}else{yaw+=(x-lastX)*.01f;tilt=Math.max(.05f,Math.min(.8f,tilt+(y-lastY)*.003f));}lastX=x;lastY=y;invalidate();}
            if(e.getActionMasked()==MotionEvent.ACTION_UP&&Math.hypot(x-downX,y-downY)<12&&objects!=null){int best=-1;double distance=70;for(int i=0;i<objects.length();i++){JSONObject o=objects.optJSONObject(i);float[] p=position(orbitIndex(o.optString("orbit")),o.optDouble("phase")+frames/(double)frameLimit*o.optDouble("energy")*.04);double d=Math.hypot(x-p[0],y-p[1]);if(d<distance){distance=d;best=i;}}
                if(best>=0){String id=objects.optJSONObject(best).optString("id");for(int i=0;i<events.length();i++)if(events.optJSONObject(i).optString("event_id").equals(id)){inspect(events.optJSONObject(i));break;}}}
            return true;
        }
    }
}
