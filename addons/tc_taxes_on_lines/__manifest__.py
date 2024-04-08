# -*- coding: utf-8 -*-
{
  "name"                 :  "Amount Taxes on Sale, Purchase and Invoice Lines",
  "summary"              :  """Amount Taxes on Sale, Purchase and Invoice Lines""",
  "category"             :  "Accounting",
  "version"              :  "1.0",
  "sequence"             :  7,
  "author"               :  "Titans Code Tech",
  "license"              :  "OPL-1",
  "website"              :  "",
  "description"          :  """Amount Taxes on Sale, Purchase and Invoice Lines""",
  "depends"              :  [
                                'sale_management','purchase','account'
                            ],
  "data"                 :  [
                                'report/tc_reports_sale_order.xml',
                                'views/tc_amount_taxes_on_line_views.xml',
                            ],
  "images"               :  ['static/description/Banner.gif'],
  "application"          :  True,
  "installable"          :  True,
  "auto_install"         :  False,
  "price"                :  10,
  "currency"             :  "USD",
  "pre_init_hook"        :  "pre_init_check",
}
