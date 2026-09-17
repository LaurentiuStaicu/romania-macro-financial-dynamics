from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright

VIEWPORTS = ((1920,1080),(1600,900),(1440,900),(1366,768),(820,1180),(390,844))


def parse_args() -> argparse.Namespace:
    parser=argparse.ArgumentParser(description="Strict World3/Macro visual-family alignment gate")
    parser.add_argument("--browser",required=True);parser.add_argument("--macro-url",required=True);parser.add_argument("--world3-url",required=True);parser.add_argument("--output",default="visual-qa")
    return parser.parse_args()


def wait_for_product(page,selector:str)->None:
    page.wait_for_load_state("domcontentloaded");page.wait_for_selector(selector,state="visible",timeout=30_000);page.wait_for_timeout(1800)


def capture(page,url:str,selector:str,output:Path)->None:
    page.goto(url,wait_until="domcontentloaded",timeout=60_000);wait_for_product(page,selector);page.screenshot(path=str(output),full_page=False)


def layout_audit(page,product:str)->dict:
    primary_selector=".primary-product" if product=="macro" else ".chart-product"
    return page.evaluate("""({primarySelector})=>{
      const visible=el=>{const s=getComputedStyle(el),r=el.getBoundingClientRect();return s.display!=='none'&&s.visibility!=='hidden'&&r.width>0&&r.height>0};
      const rects=[...document.querySelectorAll('main > section, main > details')].filter(visible).map(el=>({id:el.id||el.className,r:el.getBoundingClientRect()}));
      const overlaps=[];for(let i=0;i<rects.length;i++)for(let j=i+1;j<rects.length;j++){const a=rects[i],b=rects[j];const x=Math.max(0,Math.min(a.r.right,b.r.right)-Math.max(a.r.left,b.r.left));const y=Math.max(0,Math.min(a.r.bottom,b.r.bottom)-Math.max(a.r.top,b.r.top));if(x>1&&y>1)overlaps.push([a.id,b.id])}
      const smallControls=[...document.querySelectorAll('button,select,input:not([type="checkbox"]):not([type="radio"]),.quiet')].filter(visible).map(el=>({label:(el.textContent||el.getAttribute('aria-label')||el.id||el.tagName).trim().slice(0,80),h:el.getBoundingClientRect().height,w:el.getBoundingClientRect().width})).filter(x=>x.h<32);
      const primary=document.querySelector(primarySelector)?.getBoundingClientRect();return{viewport:[innerWidth,innerHeight],horizontalOverflow:document.documentElement.scrollWidth>innerWidth+1,panelOverlaps:overlaps,smallControls,primaryWidth:primary?.width||0,viewportShare:primary?primary.width/innerWidth:0};
    }""",{"primarySelector":primary_selector})


def computed_contract(page,product:str)->dict:
    primary=".primary-product" if product=="macro" else ".chart-product"
    return page.evaluate("""({primary})=>{const css=s=>getComputedStyle(document.querySelector(s));const body=css('body'),header=css('.product-header'),brand=css('.brand'),img=css('.brand img'),h1=css('.brand h1'),sub=css('.brand p'),lang=css('.lang'),active=css('.lang button[aria-pressed="true"]'),main=css('main'),q=css('.question-band'),panel=css(primary),quiet=css('.quiet');const pack=(s,keys)=>Object.fromEntries(keys.map(k=>[k,s[k]]));return{body:pack(body,['fontFamily','backgroundColor','color']),header:pack(header,['minHeight','paddingTop','paddingRight','paddingBottom','paddingLeft','gap','backgroundColor','borderBottomColor','backdropFilter']),brand:pack(brand,['gap']),icon:pack(img,['width','height']),title:pack(h1,['fontSize']),subtitle:pack(sub,['fontSize','color']),language:pack(lang,['borderTopColor','borderTopWidth','borderRadius']),languageActive:pack(active,['backgroundColor','color','paddingTop','paddingRight','paddingBottom','paddingLeft']),main:pack(main,['maxWidth','paddingTop','paddingRight','paddingBottom','paddingLeft']),questionBand:pack(q,['minHeight','marginBottom','borderBottomColor']),primaryPanel:pack(panel,['backgroundColor','borderTopColor','borderRadius','boxShadow']),quiet:pack(quiet,['backgroundColor','color','borderTopColor','borderRadius','paddingTop','paddingRight','paddingBottom','paddingLeft'])}}""",{"primary":primary})


def compare_contract(world:dict,macro:dict)->list[dict]:
    mismatches=[]
    for group,world_values in world.items():
        macro_values=macro.get(group,{})
        for key,value in world_values.items():
            if macro_values.get(key)!=value:mismatches.append({"property":f"{group}.{key}","world3":value,"macro":macro_values.get(key)})
    return mismatches


def side_by_side(left_path:Path,right_path:Path,output:Path,label:str)->None:
    left=Image.open(left_path).convert("RGB");right=Image.open(right_path).convert("RGB")
    if left.size!=right.size:raise SystemExit(f"Comparison images differ at {label}: {left.size} vs {right.size}")
    canvas=Image.new("RGB",(left.width*2,left.height+34),"white");canvas.paste(left,(0,34));canvas.paste(right,(left.width,34));draw=ImageDraw.Draw(canvas);draw.text((12,10),f"WORLD3 PRODUCT RECOVERY | {label}",fill="black");draw.text((left.width+12,10),f"MACRO STRICT ALIGNMENT | {label}",fill="black");canvas.save(output)


def main()->None:
    args=parse_args();root=Path(args.output);macro_dir=root/'macro';world_dir=root/'world3';side_dir=root/'side-by-side';audit_dir=root/'audit'
    for d in (macro_dir,world_dir,side_dir,audit_dir):d.mkdir(parents=True,exist_ok=True)
    report={"gate":"Strict World3 Visual Alignment Gate","canonical_product":"World3 Product Recovery PR #10 @ 51e236b61a0ec169bc8f28d4f8192e450ab6bd6d","candidate_product":"Romania Macro-Financial Dynamics","viewports":{},"css_parity":"PENDING","functional_layout":"PENDING","human_visual_comparison":"REQUIRES_SCREENSHOT_INSPECTION"}
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=args.browser,headless=True,args=['--no-sandbox','--disable-gpu'])
        try:
            for width,height in VIEWPORTS:
                label=f"{width}x{height}";macro_path=macro_dir/f"{label}.png";world_path=world_dir/f"{label}.png"
                mctx=browser.new_context(viewport={"width":width,"height":height},color_scheme="light",device_scale_factor=1);mpage=mctx.new_page();capture(mpage,args.macro_url,'.product-header',macro_path);maudit=layout_audit(mpage,'macro');mcontract=computed_contract(mpage,'macro');mctx.close()
                wctx=browser.new_context(viewport={"width":width,"height":height},color_scheme="light",device_scale_factor=1);wpage=wctx.new_page();capture(wpage,args.world3_url,'.product-header',world_path);waudit=layout_audit(wpage,'world3');wcontract=computed_contract(wpage,'world3');wctx.close()
                expected=[width,height]
                for name,audit in (("Macro",maudit),("World3",waudit)):
                    if audit['viewport']!=expected:raise SystemExit(f"{name} exact viewport failure at {label}: {audit['viewport']}")
                    if audit['horizontalOverflow']:raise SystemExit(f"{name} horizontal overflow at {label}")
                    if audit['panelOverlaps']:raise SystemExit(f"{name} panel overlap at {label}: {audit['panelOverlaps']}")
                    if audit['smallControls']:raise SystemExit(f"{name} controls below 32px at {label}: {audit['smallControls']}")
                mismatches=compare_contract(wcontract,mcontract)
                if mismatches:raise SystemExit(f"Shared computed visual primitives differ at {label}: {mismatches}")
                side_by_side(world_path,macro_path,side_dir/f"{label}.png",label);report['viewports'][label]={"macro":maudit,"world3":waudit,"sharedComputedPrimitives":"MATCH"}
        finally:browser.close()
    report['css_parity']='PASS';report['functional_layout']='PASS';(audit_dir/'visual-gate-report.json').write_text(json.dumps(report,indent=2,sort_keys=True),encoding='utf-8');print(json.dumps(report,indent=2,sort_keys=True))


if __name__=='__main__':main()
