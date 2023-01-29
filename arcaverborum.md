# Arca Verborum

Arca Verborum is a project to interface with the data from the GLED package.

The main available function is currently the one for performing weighted sampling of
languages based on their phylogenetic distance. See code for more documentation, as below.

```python
>>> import arcaverborum
>>> matrix = arcaverborum.read_default_matrix()
>>> arcaverborum.language_sample(matrix, 5)
('GalibiCarib_gali1262', 'DonnoSoDogon_donn1239', 'NorthernAmami-Oshima_nort2935', 'KolPapuaNewGuinea_kolp1236', 'Kiliwa_kili1268')
```