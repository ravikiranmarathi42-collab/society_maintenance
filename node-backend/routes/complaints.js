const express = require('express');
const pool = require('../config/db');
const apiKey = require('../middleware/apiKey');
const router = express.Router();
router.use(apiKey);

router.get('/', async (req, res, next) => {
  try {
    const [rows] = await pool.execute(`SELECT c.id,c.subject,c.category,c.priority,c.status,c.admin_remarks,c.created_at,
      r.full_name resident_name,f.flat_number,s.full_name assigned_staff
      FROM complaints c JOIN residents r ON r.id=c.resident_id JOIN flats f ON f.id=c.flat_id
      LEFT JOIN staff s ON s.id=c.assigned_staff_id ORDER BY c.created_at DESC LIMIT 500`);
    res.json({ data: rows });
  } catch (err) { next(err); }
});

router.patch('/:id/status', async (req, res, next) => {
  try {
    const id = Number(req.params.id);
    const { status, admin_remarks = '', assigned_staff_id = null } = req.body || {};
    const allowed = ['Submitted', 'Assigned', 'In Progress', 'Resolved', 'Closed'];
    if (!Number.isInteger(id) || id < 1 || !allowed.includes(status)) {
      return res.status(400).json({ error: 'Invalid complaint ID or status.' });
    }
    if (assigned_staff_id !== null && (!Number.isInteger(Number(assigned_staff_id)) || Number(assigned_staff_id) < 1)) {
      return res.status(400).json({ error: 'assigned_staff_id must be a positive integer or null.' });
    }
    const [result] = await pool.execute(
      `UPDATE complaints SET status=?, admin_remarks=?, assigned_staff_id=?,
       resolved_at=CASE WHEN ?='Resolved' THEN COALESCE(resolved_at,NOW()) ELSE resolved_at END WHERE id=?`,
      [status, String(admin_remarks).slice(0, 5000), assigned_staff_id === null ? null : Number(assigned_staff_id), status, id]
    );
    if (!result.affectedRows) return res.status(404).json({ error: 'Complaint not found.' });
    res.json({ message: 'Complaint updated.', id, status });
  } catch (err) { next(err); }
});
module.exports = router;
