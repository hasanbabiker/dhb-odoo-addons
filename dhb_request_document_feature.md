# إضافة: زر "اطلب مستندًا من المتدرب"

تعديل على موديول القبول في `dhb.registration.invite`.

## المشكلة

أثناء مراجعة الطلب قد يجد المراجع أن صورة الهوية غير مقروءة، أو أن مستندًا ناقصًا. حاليًا:

- رابط التسجيل الأصلي **يُستهلك بعد الاستخدام مرة واحدة**، فلا يمكن إعادة فتحه للمتدرب.
- حقول الهوية في تبويب Identity **للقراءة فقط** (مرآة عن `res.partner`)، فلا يستطيع المراجع الرفع من مكانه.
- الحل الوحيد اليوم: مراسلة المتدرب يدويًا، ثم فتح `Contacts` والرفع هناك — خطوتان خارج الطلب، بلا أثر مسجّل.

لاحظ أن الحالة `chase_documents` **موجودة أصلًا** في `next_action` — الفكرة كانت في التصميم، لكن الآلية التي تنفّذها غير موجودة.

## الحل

نموذج جديد `dhb.learner.document` يعمل بنفس نمط `dhb.payment.proof` الموجود لديك: طلب مستند برمز سري، رابط عام للمتدرب، يرفع ملفًا واحدًا فقط، يصل بحالة "بانتظار المراجعة"، وعند قبوله **يُكتب تلقائيًا على سجل جهة الاتصال** — فيظهر في الطلب وفي تطبيق Contacts معًا.

---

## 1) النموذج الجديد

`models/dhb_learner_document.py`

```python
import secrets
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class DhbLearnerDocument(models.Model):
    _name = "dhb.learner.document"
    _description = "Document requested from a learner"
    _inherit = ["mail.thread"]
    _order = "create_date desc"

    # الحقل الذي يستقبل الملف على سجل المتدرب عند القبول.
    # المفتاح هو ما يختاره المراجع، والقيمة هي الحقل على res.partner.
    TARGET_FIELDS = {
        "id_document": ("id_document_file", "id_document_filename"),
        "photo": ("image_1920", None),
    }

    name = fields.Char(
        string="Reference", readonly=True, copy=False, default=lambda s: _("New")
    )
    invite_id = fields.Many2one(
        "dhb.registration.invite",
        string="Application",
        required=True,
        ondelete="cascade",
        index=True,
    )
    partner_id = fields.Many2one(
        related="invite_id.partner_id", string="Learner", store=True, readonly=True
    )
    doc_type = fields.Selection(
        [
            ("id_document", "Identity document"),
            ("photo", "Photograph"),
            ("other", "Something else"),
        ],
        string="What is being asked for",
        required=True,
        default="id_document",
        help="Identity document and Photograph are written onto the learner's "
             "contact record when accepted. Anything else stays on this request "
             "as an attachment.",
    )
    reason = fields.Char(
        string="Why",
        required=True,
        help="Shown to the learner on the upload page. Say what was wrong with "
             "the first one, e.g. the corners are cut off.",
    )

    token = fields.Char(readonly=True, copy=False, groups="base.group_user")
    url = fields.Char(string="Upload link", compute="_compute_url")
    expiry_date = fields.Date(
        string="Valid until",
        default=lambda s: fields.Date.today() + timedelta(days=14),
    )

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("sent", "Waiting on the learner"),
            ("uploaded", "Uploaded, not checked"),
            ("accepted", "Accepted"),
            ("rejected", "Rejected"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )

    file = fields.Binary(string="File", attachment=True, copy=False)
    filename = fields.Char(string="File name")
    uploaded_on = fields.Datetime(readonly=True)
    uploaded_ip = fields.Char(string="From IP", readonly=True)

    requested_by = fields.Many2one("res.users", readonly=True, default=lambda s: s.env.user)
    sent_on = fields.Datetime(readonly=True)
    reviewed_by = fields.Many2one("res.users", readonly=True)
    reviewed_on = fields.Datetime(readonly=True)
    review_note = fields.Text(string="Note")

    reminder_count = fields.Integer(readonly=True, default=0)
    last_reminder_on = fields.Datetime(readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "dhb.learner.document"
                ) or _("New")
            if not vals.get("token"):
                vals["token"] = secrets.token_urlsafe(32)
        return super().create(vals_list)

    def _compute_url(self):
        base = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        for rec in self:
            rec.url = (
                f"{base}/learner/document/{rec.token}" if rec.token else False
            )

    # ---------------------------------------------------------------- actions

    def action_send(self):
        """Send the learner the link and start waiting."""
        template = self.env.ref(
            "dhb_admissions.mail_template_learner_document_request",
            raise_if_not_found=False,
        )
        for rec in self:
            if rec.state not in ("draft", "sent", "rejected"):
                raise UserError(_("This request has already been dealt with."))
            if not rec.invite_id.email:
                raise UserError(_("The application has no email address."))
            if template:
                template.send_mail(rec.id, force_send=True)
            rec.write({
                "state": "sent",
                "sent_on": fields.Datetime.now(),
                "reminder_count": rec.reminder_count + (1 if rec.state == "sent" else 0),
                "last_reminder_on": fields.Datetime.now() if rec.state == "sent" else False,
            })
            rec.invite_id.message_post(
                body=_("Asked the learner for: %s — %s") % (
                    dict(rec._fields["doc_type"].selection).get(rec.doc_type),
                    rec.reason,
                )
            )
        return True

    def action_accept(self):
        """Put the file where it belongs and close the request."""
        for rec in self:
            if not rec.file:
                raise UserError(_("Nothing has been uploaded yet."))
            target = self.TARGET_FIELDS.get(rec.doc_type)
            if target and rec.partner_id:
                file_field, name_field = target
                values = {file_field: rec.file}
                if name_field:
                    values[name_field] = rec.filename
                rec.partner_id.sudo().write(values)
            rec.write({
                "state": "accepted",
                "reviewed_by": self.env.user.id,
                "reviewed_on": fields.Datetime.now(),
            })
            rec.invite_id.message_post(
                body=_("Accepted the replacement %s.") % (
                    dict(rec._fields["doc_type"].selection).get(rec.doc_type)
                ),
                attachment_ids=rec._attachment_ids().ids,
            )
        return True

    def action_reject(self):
        """Not good enough either — ask again with the same link."""
        for rec in self:
            rec.write({
                "state": "rejected",
                "reviewed_by": self.env.user.id,
                "reviewed_on": fields.Datetime.now(),
            })
        return True

    def action_cancel(self):
        self.write({"state": "cancelled"})
        return True

    def _attachment_ids(self):
        return self.env["ir.attachment"].search([
            ("res_model", "=", self._name),
            ("res_id", "in", self.ids),
            ("res_field", "=", "file"),
        ])
```

---

## 2) الصفحة العامة للمتدرب

`controllers/learner_document.py`

```python
import base64

from odoo import http, fields, _
from odoo.http import request


class LearnerDocumentController(http.Controller):

    def _get_request(self, token):
        rec = request.env["dhb.learner.document"].sudo().search(
            [("token", "=", token)], limit=1
        )
        if not rec:
            return None
        if rec.state in ("accepted", "cancelled"):
            return None
        if rec.expiry_date and rec.expiry_date < fields.Date.today():
            return None
        return rec

    @http.route(
        "/learner/document/<string:token>",
        type="http", auth="public", website=True, sitemap=False,
    )
    def upload_form(self, token, **kw):
        doc_request = self._get_request(token)
        if not doc_request:
            return request.render("dhb_admissions.learner_link_not_valid")
        return request.render(
            "dhb_admissions.learner_document_upload",
            {"req": doc_request, "error": kw.get("error")},
        )

    @http.route(
        "/learner/document/<string:token>/submit",
        type="http", auth="public", website=True, csrf=True, methods=["POST"],
    )
    def upload_submit(self, token, **post):
        doc_request = self._get_request(token)
        if not doc_request:
            return request.render("dhb_admissions.learner_link_not_valid")

        upload = post.get("file")
        if not upload or not upload.filename:
            return request.redirect(
                f"/learner/document/{token}?error=missing"
            )

        content = upload.read()
        # 10 MB ceiling, and only the types a reviewer can actually open.
        if len(content) > 10 * 1024 * 1024:
            return request.redirect(f"/learner/document/{token}?error=too_big")
        allowed = ("image/jpeg", "image/png", "image/heic", "application/pdf")
        if upload.content_type not in allowed:
            return request.redirect(f"/learner/document/{token}?error=type")

        doc_request.sudo().write({
            "file": base64.b64encode(content),
            "filename": upload.filename,
            "uploaded_on": fields.Datetime.now(),
            "uploaded_ip": request.httprequest.remote_addr,
            "state": "uploaded",
        })
        doc_request.invite_id.sudo().message_post(
            body=_("The learner uploaded a replacement document.")
        )
        doc_request.invite_id.sudo().activity_schedule(
            "mail.mail_activity_data_todo",
            user_id=doc_request.requested_by.id or request.env.uid,
            summary=_("Check the document the learner sent"),
            note=doc_request.reason or "",
        )
        return request.render("dhb_admissions.learner_document_thanks", {
            "req": doc_request,
        })
```

**ملاحظة أمنية:** الرابط يُستهلك عند **القبول** لا عند الرفع — حتى إذا رفع المتدرب صورة رديئة ثانيةً، يستطيع الرفع مرة أخرى بنفس الرابط دون أن تطلب له رابطًا جديدًا.

---

## 3) صفحة الرفع

`views/learner_document_templates.xml`

```xml
<odoo>
  <template id="learner_document_upload" name="Upload a document">
    <t t-call="website.layout">
      <div class="container my-5" style="max-width: 640px;">
        <h2>مستند مطلوب</h2>
        <p class="text-muted">
          مرحبًا <t t-esc="req.invite_id.learner_name or ''"/>،
          نحتاج منك رفع مستند لإكمال تسجيلك في
          <strong t-esc="req.invite_id.event_id.name"/>.
        </p>

        <div class="alert alert-info">
          <strong>المطلوب:</strong>
          <t t-esc="dict(req._fields['doc_type'].selection).get(req.doc_type)"/><br/>
          <t t-esc="req.reason"/>
        </div>

        <t t-if="error == 'missing'">
          <div class="alert alert-danger">لم تختر ملفًا.</div>
        </t>
        <t t-if="error == 'too_big'">
          <div class="alert alert-danger">الملف أكبر من 10 ميغابايت.</div>
        </t>
        <t t-if="error == 'type'">
          <div class="alert alert-danger">
            الملفات المقبولة: صورة (JPG أو PNG) أو PDF.
          </div>
        </t>

        <form t-attf-action="/learner/document/#{req.token}/submit"
              method="post" enctype="multipart/form-data">
          <input type="hidden" name="csrf_token" t-att-value="request.csrf_token()"/>
          <div class="mb-3">
            <label class="form-label">اختر الملف</label>
            <input type="file" name="file" class="form-control"
                   accept="image/jpeg,image/png,image/heic,application/pdf" required="1"/>
            <div class="form-text">
              تأكد أن الصورة واضحة وأن أطراف المستند كاملة وغير مقصوصة.
            </div>
          </div>
          <button type="submit" class="btn btn-primary">إرسال</button>
        </form>
      </div>
    </t>
  </template>

  <template id="learner_document_thanks" name="Document received">
    <t t-call="website.layout">
      <div class="container my-5" style="max-width: 640px;">
        <h2>وصلنا المستند</h2>
        <p>شكرًا لك. سيراجعه فريق القبول ونعود إليك إن احتجنا شيئًا آخر.</p>
      </div>
    </t>
  </template>
</odoo>
```

---

## 4) الزر في الطلب

`models/dhb_registration_invite.py` — إضافة:

```python
    document_request_ids = fields.One2many(
        "dhb.learner.document", "invite_id", string="Documents asked for"
    )
    document_request_pending = fields.Integer(
        compute="_compute_document_request_pending", string="Awaiting documents"
    )

    @api.depends("document_request_ids.state")
    def _compute_document_request_pending(self):
        for rec in self:
            rec.document_request_pending = len(
                rec.document_request_ids.filtered(
                    lambda r: r.state in ("sent", "uploaded", "rejected")
                )
            )

    def action_request_document(self):
        """Open a blank request, pre-filled against this application."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Ask the learner for a document"),
            "res_model": "dhb.learner.document",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_invite_id": self.id,
                "default_doc_type": "id_document",
            },
        }

    def action_open_learner(self):
        """The reviewer needs the contact record; do not make them search."""
        self.ensure_one()
        if not self.partner_id:
            raise UserError(_("No learner contact on this application yet."))
        return {
            "type": "ir.actions.act_window",
            "res_model": "res.partner",
            "res_id": self.partner_id.id,
            "view_mode": "form",
            "target": "current",
        }
```

وفي حساب `next_action`، قبل فحص الإقرار:

```python
        if rec.document_request_pending:
            rec.next_action = "chase_documents"
            continue
```

`views/dhb_registration_invite_views.xml` — في `<header>`:

```xml
<button name="action_request_document" type="object"
        string="Ask for a document"
        class="btn-secondary"
        invisible="state not in ('submitted', 'review')"/>
```

وفي تبويب Identity، فوق الحقول مباشرة:

```xml
<button name="action_open_learner" type="object"
        string="Open the learner's record"
        icon="fa-external-link" class="btn-link"
        help="These fields live on the contact. Edit them there."/>
```

وتبويب جديد:

```xml
<page string="Documents asked for" name="document_requests">
  <field name="document_request_ids" nolabel="1">
    <list decoration-warning="state in ('sent','rejected')"
          decoration-info="state == 'uploaded'"
          decoration-success="state == 'accepted'">
      <field name="name"/>
      <field name="doc_type"/>
      <field name="reason"/>
      <field name="state"/>
      <field name="uploaded_on"/>
      <button name="action_accept" type="object" string="Accept"
              icon="fa-check" invisible="state != 'uploaded'"/>
      <button name="action_reject" type="object" string="Reject"
              icon="fa-times" invisible="state != 'uploaded'"/>
    </list>
  </field>
</page>
```

---

## 5) قالب البريد

`data/mail_templates.xml`

```xml
<record id="mail_template_learner_document_request" model="mail.template">
  <field name="name">Admissions: document requested</field>
  <field name="model_id" ref="model_dhb_learner_document"/>
  <field name="subject">مستند مطلوب لإكمال تسجيلك</field>
  <field name="email_to">{{ object.invite_id.email }}</field>
  <field name="body_html" type="html">
    <div style="direction: rtl; font-family: sans-serif;">
      <p>مرحبًا <t t-out="object.invite_id.learner_name or ''"/>،</p>
      <p>
        لإكمال تسجيلك في
        <strong t-out="object.invite_id.event_id.name or ''"/>
        نحتاج منك رفع مستند:
      </p>
      <p style="background:#fff8e1; padding:12px; border-radius:6px;">
        <t t-out="object.reason or ''"/>
      </p>
      <p>
        <a t-att-href="object.url"
           style="background:#1a3a5c; color:#fff; padding:10px 20px;
                  border-radius:4px; text-decoration:none;">
          ارفع المستند
        </a>
      </p>
      <p style="color:#888; font-size:12px;">
        الرابط صالح حتى <t t-out="object.expiry_date or ''"/>.
      </p>
      <p>DHB Training and Consulting</p>
    </div>
  </field>
</record>
```

---

## 6) التسلسل والصلاحيات

`data/ir_sequence.xml`

```xml
<record id="seq_dhb_learner_document" model="ir.sequence">
  <field name="name">Learner document request</field>
  <field name="code">dhb.learner.document</field>
  <field name="prefix">DOC</field>
  <field name="padding">5</field>
</record>
```

`security/ir.model.access.csv`

```csv
access_dhb_learner_document_user,dhb.learner.document.user,model_dhb_learner_document,base.group_user,1,1,1,0
```

---

## التحقق بعد التطبيق

1. رقّ الموديول: `-u dhb_admissions`
2. افتح طلبًا بحالة Under review ← اضغط **Ask for a document** ← اكتب السبب ← أرسل
3. الطلب ينتقل إلى `chase_documents` ويظهر في **What needs attention**
4. افتح الرابط من بريد المتدرب وارفع صورة
5. ارجع للطلب: الحالة `uploaded` ونشاط مجدول باسمك
6. اضغط **Accept** ← افتح `Contacts` وتأكد أن الصورة حلّت مكان القديمة

---

## يبقى خارج هذا التعديل

تعديلان لاحظناهما ولم يعالجهما هذا الملف:

1. **نموذج التسجيل يقبل الإرسال بلا جنسية ولا رقم مستند** — كلاهما إلزامي في ملف رفع بيانات الطلاب لدى NEBOSH. يجب أن يرفض النموذج الإرسال بدونهما.
2. **حقلا "المؤهل" و"لغة التدريس" فارغان على الدورات** — فيبقيان فارغين في كل دفعة وسجل قبول يُبنى عليها.
