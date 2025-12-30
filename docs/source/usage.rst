#######
 Usage
#######

***************
 Basic example
***************

.. code:: python

   from svg_path_editor import SvgPath, change_path_origin, optimize_path, reverse_path

   path = SvgPath("M-15 14s5 7.5 15 7.5 15-7.5 15-7.5 z")

   print(path)
   print(path.as_string(decimals=1, minify=True))
