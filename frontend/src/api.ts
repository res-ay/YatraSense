export const API=import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api';
export const ADMIN=API.replace(/\/api\/?$/,'')+'/admin/';
export type Photo={id:number;image:string;caption:string;credit:string;license:string;source_url:string};
export type Destination={id:string;name:string;area:string;destination_type:string;description:string;latitude:number;longitude:number;coordinate_source:string;popularity_score:number;popularity:string;activities:string[];specific_activities:string;photos:Photo[];model_coverage:string};
export type Result={destination_id:string;name:string;area:string;crowd:string;recommendation_score:number;popularity:string;matched_activities:string[];weather:{temperature_c:number;rainfall_mm_month:number;wind_kmh:number;kind:string};estimate_note:string;new_destination:boolean;destination:Destination};
export type Plan={results:Result[];travel_date:string;message:string|null;saved_trip_id?:number;synthetic:boolean};
export const activityOptions=[{id:'heritage_pilgrimage',label:'Heritage & pilgrimage',icon:'⌂',description:'Temples, museums & cultural walks'},{id:'trekking_hiking',label:'Trekking & hiking',icon:'△',description:'Trails, walking & mountain journeys'},{id:'wildlife_birdwatching',label:'Wildlife & birdwatching',icon:'♧',description:'No matching places in this demo catalog'},{id:'boating_water',label:'Boating & water',icon:'≈',description:'Lakes and boating experiences'},{id:'adventure_sports',label:'Adventure sports',icon:'↗',description:'Adventure activity destinations'}];
export const areas=['All','Kathmandu','Lalitpur','Bhaktapur','Pokhara','Mountain regions'];
export function label(id:string){return activityOptions.find(a=>a.id===id)?.label || id;}
export async function api<T>(path:string,options:RequestInit={}):Promise<T>{
 const token=localStorage.getItem('yatrasense-organic-token');
 let response:Response;
 try {response=await fetch(API+path,{...options,headers:{'Content-Type':'application/json',...(token?{Authorization:`Token ${token}`}:{ }),...options.headers}});}
 catch {throw new Error('Cannot reach Django. Start the backend on port 8000.');}
 if(response.status===204)return undefined as T;
 const text=await response.text();let data:any;
 try{data=JSON.parse(text);}catch{throw new Error(`The server returned an unreadable response (${response.status}). Check the backend terminal.`);}
 if(!response.ok){if(response.status===401){localStorage.removeItem('yatrasense-organic-token');}
 throw new Error(data.detail || Object.entries(data).map(([k,v])=>`${k}: ${Array.isArray(v)?v.join(' '):String(v)}`).join(' · ') || 'Request failed.');}
 return data;
}
