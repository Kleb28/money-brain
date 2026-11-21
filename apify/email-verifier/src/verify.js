// Pure logic: syntax check, DNS-over-HTTPS answer parsing, built-in lists and the status rule.
// No network here. main.js passes in the function that performs the DNS-over-HTTPS request.
import { domainToASCII } from "node:url";

/** Addresses that go to a team or function rather than one person. Matched on the whole local part (a "+tag" is ignored). */
export const ROLE_PREFIXES = new Set(`
abuse accounting accounts admin administrator admissions ads advertising all an api apply billing bookings business
careers ceo compliance contact contactus customercare customerservice data dev developers devops dns do-not-reply
donotreply editor education enquiries enquiry events everyone feedback finance ftp hello help helpdesk hi hiring
hostmaster hr inbox info information inquiries inquiry investors invoices it jobs legal list mail mailer-daemon
marketing media membership news newsletter no-reply noc noreply notifications office operations ops orders
partners partnerships payments payroll postmaster pr press privacy purchasing recruiting recruitment registrar
reservations root sales secretary security service services shop spam staff store subscribe subscriptions
support sysadmin team tech technical test training unsubscribe usenet uucp webmaster welcome www
`.trim().split(/\s+/));

/** Free consumer mailbox providers. */
export const FREE_PROVIDERS = new Set(`
gmail.com googlemail.com yahoo.com yahoo.co.uk yahoo.co.in yahoo.co.jp yahoo.fr yahoo.de yahoo.es yahoo.it yahoo.ca
yahoo.com.br yahoo.com.au yahoo.com.mx yahoo.com.ar ymail.com rocketmail.com outlook.com outlook.fr outlook.de
outlook.es outlook.it outlook.co.uk outlook.jp hotmail.com hotmail.co.uk hotmail.fr hotmail.de hotmail.it
hotmail.es hotmail.ca live.com live.co.uk live.fr live.de live.it live.nl live.ca live.com.au msn.com
passport.com icloud.com me.com mac.com aol.com aim.com proton.me protonmail.com protonmail.ch pm.me
tutanota.com tutanota.de tuta.io tutamail.com zoho.com zohomail.com zohomail.eu yandex.com yandex.ru ya.ru
mail.ru bk.ru inbox.ru list.ru rambler.ru gmx.com gmx.de gmx.net gmx.at gmx.ch gmx.fr gmx.co.uk gmx.us web.de
t-online.de freenet.de mail.com email.com usa.com fastmail.com fastmail.fm hey.com hushmail.com qq.com
foxmail.com 163.com 126.com yeah.net sina.com sina.cn sohu.com aliyun.com 139.com naver.com hanmail.net
daum.net kakao.com nate.com orange.fr wanadoo.fr free.fr laposte.net sfr.fr libero.it virgilio.it tiscali.it
alice.it seznam.cz wp.pl o2.pl interia.pl onet.pl ukr.net rediffmail.com comcast.net verizon.net att.net
sbcglobal.net bellsouth.net cox.net charter.net earthlink.net btinternet.com sky.com shaw.ca rogers.com
bigpond.com optusnet.com.au uol.com.br bol.com.br terra.com.br mailfence.com posteo.de mailbox.org
`.trim().split(/\s+/));

/** Disposable / temporary inbox domains. A subdomain of a listed domain also counts. */
export const DISPOSABLE_DOMAINS = new Set(`
0-mail.com 0815.ru 0clickemail.com 0wnd.net 0wnd.org 10mail.org 10minutemail.co.za 10minutemail.com
10minutemail.de 10minutemail.net 10minutemail.org 10minutemail.us 10minutesmail.com 10minutemailbox.com
20minutemail.com 20minutemail.it 20email.eu 2prong.com 30minutemail.com 33mail.com 3d-painting.com
4warding.com 4warding.net 4warding.org 60minutemail.com 675hosting.com 6url.com 75hosting.com 9ox.net
a-bc.net afrobacon.com ajaxapp.net amilegit.com amiri.net amiriindustries.com anonbox.net anonymbox.com
antichef.com antichef.net antispam.de armyspy.com baxomale.ht.cx beefmilk.com binkmail.com bio-muesli.net
bobmail.info bodhi.lawlita.com bofthew.com bootybay.de boun.cr bouncr.com breakthru.com brefmail.com
bsnow.net bugmenot.com bumpymail.com burnermail.io byom.de casualdx.com centermail.com centermail.net
chammy.info chogmail.com choicemail1.com clixser.com cool.fr.nf correo.blogos.net
cosmorph.com courriel.fr.nf courrieltemporaire.com cubiclink.com curryworld.de cust.in cuvox.de dacoolest.com
dandikmail.com dayrep.com dcemail.com deadaddress.com deadspam.com delikkt.de despam.it despammed.com
devnullmail.com dfgh.net dingbone.com discard.email discardmail.com discardmail.de
disposableaddress.com disposableemailaddresses.com disposableinbox.com dispose.it disposeamail.com
disposemail.com dispostable.com dodgeit.com dodgit.com dodgit.org donemail.ru dontreg.com dontsendmespam.de
drdrb.com drdrb.net dropmail.me dump-email.info dumpandjunk.com dumpmail.de dumpyemail.com e4ward.com
easytrashmail.com einmalmail.de einrot.com eintagsmail.de email60.com emaildienst.de emailgo.de emailias.com
emailigo.de emailinfive.com emailmiser.com emailondeck.com emailsensei.com emailtemporanea.com
emailtemporanea.net emailtemporar.ro emailtemporario.com.br emailthe.net emailtmp.com emailto.de
emailwarden.com emailx.at.hm emailxfer.com emltmp.com emz.net enterto.com ephemail.net etranquil.com
etranquil.net etranquil.org evopo.com explodemail.com fakeinbox.com fakeinformation.com fakemail.fr
fakemailgenerator.com fakemailz.com fammix.com fansworldwide.de fantasymail.de fastacura.com filzmail.com
fizmail.com fleckens.hu fr33mail.info frapmail.com freundin.ru front14.org fudgerub.com fux0ringduh.com
garliclife.com getairmail.com getmails.eu getnada.com getonemail.com getonemail.net ghosttexter.de
girlsundertheinfluence.com gishpuppy.com gowikibooks.com gowikicampus.com gowikicars.com gowikifilms.com
gowikigames.com gowikimusic.com gowikinetwork.com gowikitravel.com gowikitv.com grandmamail.com
grandmasmail.com great-host.in greensloth.com grr.la gsrv.co.uk guerillamail.biz guerillamail.com
guerillamail.de guerillamail.info guerillamail.net guerillamail.org guerrillamail.biz guerrillamail.com
guerrillamail.de guerrillamail.info guerrillamail.net guerrillamail.org guerrillamailblock.com gustr.com
h8s.org harakirimail.com hatespam.org herp.in hidemail.de hidzz.com hmamail.com hochsitze.com
hopemail.biz hulapla.de ieatspam.eu ieatspam.info ieh-mail.de ihateyoualot.info iheartspam.org
imails.info inbax.tk inbox.si inboxalias.com inboxbear.com inboxclean.com inboxclean.org inboxkitten.com
incognitomail.com incognitomail.net incognitomail.org insorg-mail.info ipoo.org irish2me.com iwi.net
jetable.com jetable.fr.nf jetable.net jetable.org jnxjn.com jourrapide.com junk1e.com kasmail.com
kaspop.com keepmymail.com killmail.com killmail.net kir.ch.tc klassmaster.com klzlk.com koszmail.pl
kulturbetrieb.info kurzepost.de lawlita.com letthemeatspam.com lhsdv.com lifebyfood.com link2mail.net
litedrop.com lol.ovpn.to lookugly.com lopl.co.cc lortemail.dk lr78.com luxusmail.org m4ilweb.info
maboard.com mail-temporaire.fr mail.mezimages.net mail2rss.org mail4trash.com
mailbidon.com mailblocks.com mailcatch.com mailde.de mailde.info maildrop.cc maildx.com maileater.com
mailexpire.com mailfa.tk mailforspam.com mailfreeonline.com mailguard.me mailin8r.com mailinater.com
mailinator.com mailinator.net mailinator.org mailinator2.com mailincubator.com mailismagic.com mailme.ir
mailme.lv mailmetrash.com mailmoat.com mailnator.com mailnesia.com mailnull.com mailorg.org mailpick.biz
mailpoof.com mailrock.biz mailsac.com mailscrap.com mailshell.com mailsiphon.com mailslite.com mailtemp.info
mailtothis.com mailzilla.com mailzilla.org mbx.cc mega.zik.dj meinspamschutz.de meltmail.com
messagebeamer.de mierdamail.com mintemail.com mjukglass.nu moakt.com mobi.web.id moburl.com moncourrier.fr.nf
monemail.fr.nf monmail.fr.nf monumentmail.com mohmal.com msa.minsmail.com mt2009.com mt2014.com mx0.wwwnew.eu
mycleaninbox.net mypartyclip.de myphantomemail.com mysamp.de myspaceinc.com myspaceinc.net myspacepimpedup.com
mytempemail.com mytrashmail.com nabuma.com nepwk.com nervmich.net nervtmich.net netmails.com
netmails.net netzidiot.de neverbox.com no-spam.ws nobulk.com noclickemail.com nogmailspam.info nomail.xl.cx
nomail2me.com nomorespamemails.com nospam.ze.tc nospam4.us nospamfor.us nospammail.net nospamthanks.info
notmailinator.com nowhere.org nowmymail.com nurfuerspam.de nwldx.com objectmail.com
obobbo.com oneoffemail.com onewaymail.com oopi.org ordinaryamerican.net
ourklips.com outlawspam.com ovpn.to owlpic.com pancakemail.com pimpedupmyspace.com pjjkp.com plexolan.de
politikerclub.de poofy.org pookmail.com privy-mail.com privymail.de proxymail.eu prtnx.com
putthisinyourspamdatabase.com qq.my quickinbox.com rcpt.at reallymymail.com recode.me
recursor.net regbypass.com rejectmail.com rhyta.com rklips.com rmqkr.net
rppkn.com rtrtr.com s0ny.net safersignup.de safetymail.info safetypost.de sandelf.de
saynotospams.com selfdestructingmail.com sendspamhere.com sharklasers.com shiftmail.com shitmail.me
skeefmail.com slaskpost.se slopsbox.com smellfear.com snakemail.com sneakemail.com
sofimail.com sofort-mail.de sogetthis.com soodonims.com spam.la spam.su spam4.me spamavert.com spambob.com
spambob.net spambob.org spambog.com spambog.de spambog.ru spambox.info spambox.irishspringrealty.com
spambox.us spamcannon.com spamcannon.net spamcero.com spamcon.org spamcorptastic.com spamcowboy.com
spamcowboy.net spamcowboy.org spamday.com spamex.com spamfree24.com spamfree24.de spamfree24.eu
spamfree24.info spamfree24.net spamfree24.org spamgourmet.com spamgourmet.net spamgourmet.org spamherelots.com
spamhereplease.com spamhole.com spamify.com spaminator.de spamkill.info spaml.com spaml.de spammotel.com
spamobox.com spamoff.de spamslicer.com spamspot.com spamthis.co.uk spamthisplease.com spamtrail.com
speed.1s.fr spoofmail.de stuffmail.de supergreatmail.com supermailer.jp superrito.com superstachel.de
suremail.info teewars.org teleworm.com teleworm.us temp-mail.io temp-mail.org temp-mail.ru tempail.com
tempalias.com tempe-mail.com tempemail.biz tempemail.co.za tempemail.com tempemail.net tempinbox.co.uk
tempinbox.com tempmail.eu tempmail.it tempmail.net tempmail2.com tempmaildemo.com tempmailer.com
tempmailer.de tempmailo.com tempomail.fr temporarily.de temporarioemail.com.br temporaryemail.net
temporaryforwarding.com temporaryinbox.com temporarymailaddress.com tempr.email tempthe.net thankyou2010.com
thisisnotmyrealemail.com throwam.com throwawayemailaddress.com throwawaymail.com tilien.com tmail.ws
tmailinator.com tmpmail.net tmpmail.org toiea.com tradermail.info trash-amil.com trash-mail.at
trash-mail.com trash-mail.de trash2009.com trashdevil.com trashdevil.de trashemail.de trashmail.at
trashmail.com trashmail.de trashmail.me trashmail.net trashmail.org trashmail.ws trashmailer.com
trashymail.com trashymail.net trbvm.com trillianpro.com turual.com twinmail.de tyldd.com uggsrock.com
upliftnow.com uplipht.com venompen.com veryrealemail.com viditag.com viewcastmedia.com viewcastmedia.net
viewcastmedia.org vomoto.com vubby.com walala.org walkmail.net webemail.me webm4il.info wegwerfadresse.de
wegwerfemail.de wegwerfmail.de wegwerfmail.info wegwerfmail.net wegwerfmail.org wetrainbayarea.com
wetrainbayarea.org wh4f.org whatiaas.com whatpaas.com whatsaas.com whopy.com whyspam.me wilemail.com
willhackforfood.biz willselfdestruct.com winemaven.info wronghead.com wuzup.net wuzupmail.net wwwnew.eu
xagloo.com xemaps.com xents.com xmaily.com xoxy.net yep.it yogamaven.com yopmail.com yopmail.fr yopmail.net
ypmail.webarnak.fr.eu.org yuurok.com zehnminutenmail.de zippymail.info zoaxe.com zoemail.org
`.trim().split(/\s+/));

/** Common misspellings of large mailbox providers -> the intended domain. Explicit list, no fuzzy matching. */
export const DOMAIN_TYPOS = {
  "gmial.com": "gmail.com", "gmai.com": "gmail.com", "gmal.com": "gmail.com", "gmil.com": "gmail.com", "gamil.com": "gmail.com",
  "gnail.com": "gmail.com", "gmaill.com": "gmail.com", "gmali.com": "gmail.com", "gmail.co": "gmail.com", "gmail.con": "gmail.com",
  "gmail.cm": "gmail.com", "gmail.om": "gmail.com", "gmail.cmo": "gmail.com", "gmail.comm": "gmail.com", "gmaik.com": "gmail.com",
  "gmailc.om": "gmail.com", "gmail.vom": "gmail.com", "gmail.xom": "gmail.com", "gmsil.com": "gmail.com", "gmeil.com": "gmail.com",
  "gimail.com": "gmail.com", "gemail.com": "gmail.com", "g-mail.com": "gmail.com", "googlemial.com": "googlemail.com",
  "yaho.com": "yahoo.com", "yahooo.com": "yahoo.com", "yhoo.com": "yahoo.com", "yahoo.co": "yahoo.com", "yahoo.con": "yahoo.com",
  "yahoo.cm": "yahoo.com", "yahoo.om": "yahoo.com", "yaoo.com": "yahoo.com", "yhaoo.com": "yahoo.com", "yahho.com": "yahoo.com",
  "yahoo.comm": "yahoo.com", "yaho.co.uk": "yahoo.co.uk",
  "hotmial.com": "hotmail.com", "hotmai.com": "hotmail.com", "hotmal.com": "hotmail.com", "hotmil.com": "hotmail.com",
  "hotmaill.com": "hotmail.com", "hotmail.co": "hotmail.com", "hotmail.con": "hotmail.com", "hotmail.cm": "hotmail.com",
  "hotmail.om": "hotmail.com", "hotnail.com": "hotmail.com", "hormail.com": "hotmail.com", "hotmali.com": "hotmail.com",
  "homail.com": "hotmail.com", "htomail.com": "hotmail.com", "hotmail.comm": "hotmail.com",
  "outlok.com": "outlook.com", "outloo.com": "outlook.com", "outlook.co": "outlook.com", "outlook.con": "outlook.com",
  "outlook.cm": "outlook.com", "outlook.om": "outlook.com", "outllok.com": "outlook.com", "outlokk.com": "outlook.com",
  "oulook.com": "outlook.com", "otlook.com": "outlook.com", "outlool.com": "outlook.com", "outook.com": "outlook.com",
  "iclod.com": "icloud.com", "icoud.com": "icloud.com", "icloud.co": "icloud.com", "icloud.con": "icloud.com",
  "icloud.cm": "icloud.com", "iclould.com": "icloud.com", "icluod.com": "icloud.com", "icloude.com": "icloud.com",
  "aol.co": "aol.com", "aol.con": "aol.com", "aol.cm": "aol.com", "aoll.com": "aol.com",
  "live.con": "live.com", "live.cm": "live.com", "msn.con": "msn.com",
  "protonmial.com": "protonmail.com", "protonmai.com": "protonmail.com", "protonmail.co": "protonmail.com", "protonmail.con": "protonmail.com",
  "comcast.con": "comcast.net", "comcas.net": "comcast.net", "verizon.con": "verizon.net",
};

const LOCAL_RE = /^[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*$/i;
const LABEL_RE = /^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/;
const TLD_RE = /^(?:[a-z]{2,63}|xn--[a-z0-9-]{1,59})$/;

/** Trim, drop a "mailto:" prefix, surrounding <> and any "?subject=" tail. */
export const clean = (raw) =>
  String(raw ?? "").trim().replace(/^mailto:/i, "").replace(/\?.*$/, "").replace(/^<(.*)>$/, "$1").trim();

/** Key used to de-duplicate input: the cleaned address, lowercased. */
export const emailKey = (raw) => clean(raw).toLowerCase();

/** A string or an array of strings (as in a contact scraper's "emails" field) -> non-empty strings. */
export function collectEmails(value) {
  const list = Array.isArray(value) ? value : [value];
  return list.filter((v) => typeof v === "string").map((v) => v.trim()).filter(Boolean);
}

/**
 * Syntax check for the common "local@domain.tld" form.
 * Deliberately stricter than RFC 5322: quoted local parts, IP-literal domains and non-ASCII local parts are rejected.
 * Internationalized domains are accepted and converted to punycode.
 */
export function parseEmail(raw) {
  const email = String(raw ?? "").trim();
  const bad = { email, syntaxValid: false, normalized: null, local: null, domain: null };
  const s = clean(raw);
  const at = s.lastIndexOf("@");
  if (at < 1 || at === s.length - 1) return bad;
  const local = s.slice(0, at).toLowerCase();
  if (local.length > 64 || !LOCAL_RE.test(local)) return bad;
  const rawDomain = s.slice(at + 1).toLowerCase();
  if (/[^\p{L}\p{N}\p{M}.-]/u.test(rawDomain)) return bad;
  const domain = domainToASCII(rawDomain);
  if (!domain || domain.length > 253) return bad;
  const labels = domain.split(".");
  if (labels.length < 2 || !labels.every((l) => LABEL_RE.test(l)) || !TLD_RE.test(labels.at(-1))) return bad;
  const normalized = `${local}@${domain}`;
  if (normalized.length > 254) return bad;
  return { email, syntaxValid: true, normalized, local, domain };
}

/** True for the domain itself or any subdomain of a listed disposable domain. */
export function isDisposable(domain) {
  const labels = String(domain ?? "").toLowerCase().split(".");
  for (let i = 0; i < labels.length - 1; i++) if (DISPOSABLE_DOMAINS.has(labels.slice(i).join("."))) return true;
  return false;
}

export const isRoleBased = (local) => ROLE_PREFIXES.has(String(local ?? "").toLowerCase().split("+")[0]);
export const isFreeProvider = (domain) => FREE_PROVIDERS.has(String(domain ?? "").toLowerCase());

/** Suggested corrected address for a known provider typo, else null. */
export function didYouMean(local, domain) {
  const fix = Object.hasOwn(DOMAIN_TYPOS, domain) ? DOMAIN_TYPOS[domain] : null;
  return fix ? `${local}@${fix}` : null;
}

/**
 * DNS-over-HTTPS JSON answer for an MX query -> hosts sorted by priority.
 * Shape: {"Status":0,"Answer":[{"name":"x.","type":15,"TTL":300,"data":"10 mx.example.com."}]}
 * A "null MX" (RFC 7505, data "0 .") means the domain declares that it accepts no mail.
 */
export function parseMx(json) {
  const records = [];
  for (const a of json?.Answer ?? []) {
    if (a?.type !== 15) continue; // skips CNAMEs that can precede the MX records
    const m = /^\s*(\d+)\s+(\S+)\s*$/.exec(String(a.data ?? ""));
    if (!m) continue;
    records.push({ priority: Number(m[1]), host: m[2].replace(/\.$/, "").toLowerCase() });
  }
  const real = records.filter((r) => r.host);
  real.sort((a, b) => a.priority - b.priority || (a.host < b.host ? -1 : a.host > b.host ? 1 : 0));
  return { mxHosts: [...new Set(real.map((r) => r.host))], nullMx: records.length > 0 && real.length === 0 };
}

const hasType = (json, type) => (json?.Answer ?? []).some((a) => a?.type === type);

/**
 * Resolve what is needed for one domain. `query(name, type)` must return the DNS-over-HTTPS JSON or throw.
 * MX first; only when there is no MX at all, A then AAAA (RFC 5321 fallback: mail goes to the address record).
 * Never throws: a failed lookup comes back as { error }.
 */
export async function lookupDomain(domain, query) {
  const out = { exists: true, mxHosts: [], nullMx: false, hasAddress: false, error: null };
  try {
    const mx = await query(domain, "MX");
    if (mx?.Status === 3) return { ...out, exists: false }; // NXDOMAIN
    Object.assign(out, parseMx(mx));
    if (out.nullMx || out.mxHosts.length) return out;
    out.hasAddress = hasType(await query(domain, "A"), 1) || hasType(await query(domain, "AAAA"), 28);
    return out;
  } catch (err) {
    return { ...out, error: String(err?.message ?? err) };
  }
}

/**
 * Final item for one email. `dns` is the lookupDomain result (ignored when the syntax is invalid).
 * invalid = bad syntax, or the domain accepts no mail; risky = disposable or role-based
 * (or the DNS lookup itself failed, so nothing could be confirmed); valid otherwise.
 */
export function verdict(parsed, dns) {
  const item = {
    email: parsed.email, normalized: parsed.normalized, status: "invalid", reason: "invalid_syntax",
    syntaxValid: parsed.syntaxValid, domain: parsed.domain, hasMx: null, mxHosts: [], acceptsMail: null,
    disposable: false, roleBased: false, freeProvider: false, didYouMean: null,
  };
  if (!parsed.syntaxValid) return item;
  item.disposable = isDisposable(parsed.domain);
  item.roleBased = isRoleBased(parsed.local);
  item.freeProvider = isFreeProvider(parsed.domain);
  item.didYouMean = didYouMean(parsed.local, parsed.domain);
  const flag = item.disposable ? "disposable" : item.roleBased ? "role_based" : null;
  if (!dns || dns.error) return { ...item, status: "risky", reason: "dns_lookup_failed" };
  item.hasMx = dns.mxHosts.length > 0;
  item.mxHosts = dns.mxHosts;
  item.acceptsMail = item.hasMx || (!dns.nullMx && dns.hasAddress);
  if (!item.acceptsMail) {
    item.reason = !dns.exists ? "domain_not_found" : dns.nullMx ? "null_mx" : "no_mx_or_address_record";
    return item;
  }
  item.status = flag ? "risky" : "valid";
  item.reason = flag ?? (item.hasMx ? "ok" : "ok_address_record_fallback");
  return item;
}
