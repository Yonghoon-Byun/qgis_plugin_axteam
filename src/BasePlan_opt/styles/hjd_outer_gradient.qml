<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis version="3.34" styleCategories="Symbology">
  <renderer-v2 type="singleSymbol" symbollevels="1" enableorderby="0" forceraster="0">
    <symbols>
      <symbol type="line" name="0" alpha="1" clip_to_extent="1" force_rhr="0">

        <!-- 7. 가장 바깥쪽 - 가장 연한 회색 (offset +36m, 오른쪽) -->
        <layer class="GeometryGenerator" enabled="1" pass="0" locked="0">
          <Option type="Map">
            <Option type="QString" name="SymbolType" value="Line"/>
            <Option type="QString" name="geometryModifier" value="offset_curve($geometry, 36)"/>
          </Option>
          <symbol type="line" name="@0@0" alpha="1" clip_to_extent="1" force_rhr="0">
            <layer class="SimpleLine" enabled="1" pass="0" locked="0">
              <Option type="Map">
                <Option type="QString" name="line_color" value="221,221,221,255"/>
                <Option type="QString" name="line_style" value="solid"/>
                <Option type="QString" name="line_width" value="6"/>
                <Option type="QString" name="line_width_unit" value="MapUnit"/>
                <Option type="QString" name="joinstyle" value="round"/>
                <Option type="QString" name="capstyle" value="round"/>
              </Option>
            </layer>
          </symbol>
        </layer>

        <!-- 6. 연한 회색 (offset +30m) -->
        <layer class="GeometryGenerator" enabled="1" pass="1" locked="0">
          <Option type="Map">
            <Option type="QString" name="SymbolType" value="Line"/>
            <Option type="QString" name="geometryModifier" value="offset_curve($geometry, 30)"/>
          </Option>
          <symbol type="line" name="@0@1" alpha="1" clip_to_extent="1" force_rhr="0">
            <layer class="SimpleLine" enabled="1" pass="0" locked="0">
              <Option type="Map">
                <Option type="QString" name="line_color" value="170,170,170,255"/>
                <Option type="QString" name="line_style" value="solid"/>
                <Option type="QString" name="line_width" value="6"/>
                <Option type="QString" name="line_width_unit" value="MapUnit"/>
                <Option type="QString" name="joinstyle" value="round"/>
                <Option type="QString" name="capstyle" value="round"/>
              </Option>
            </layer>
          </symbol>
        </layer>

        <!-- 5. 진한 회색 (offset +24m) -->
        <layer class="GeometryGenerator" enabled="1" pass="2" locked="0">
          <Option type="Map">
            <Option type="QString" name="SymbolType" value="Line"/>
            <Option type="QString" name="geometryModifier" value="offset_curve($geometry, 24)"/>
          </Option>
          <symbol type="line" name="@0@2" alpha="1" clip_to_extent="1" force_rhr="0">
            <layer class="SimpleLine" enabled="1" pass="0" locked="0">
              <Option type="Map">
                <Option type="QString" name="line_color" value="102,102,102,255"/>
                <Option type="QString" name="line_style" value="solid"/>
                <Option type="QString" name="line_width" value="6"/>
                <Option type="QString" name="line_width_unit" value="MapUnit"/>
                <Option type="QString" name="joinstyle" value="round"/>
                <Option type="QString" name="capstyle" value="round"/>
              </Option>
            </layer>
          </symbol>
        </layer>

        <!-- 4. 진한 회색 (offset +18m) -->
        <layer class="GeometryGenerator" enabled="1" pass="3" locked="0">
          <Option type="Map">
            <Option type="QString" name="SymbolType" value="Line"/>
            <Option type="QString" name="geometryModifier" value="offset_curve($geometry, 18)"/>
          </Option>
          <symbol type="line" name="@0@3" alpha="1" clip_to_extent="1" force_rhr="0">
            <layer class="SimpleLine" enabled="1" pass="0" locked="0">
              <Option type="Map">
                <Option type="QString" name="line_color" value="102,102,102,255"/>
                <Option type="QString" name="line_style" value="solid"/>
                <Option type="QString" name="line_width" value="6"/>
                <Option type="QString" name="line_width_unit" value="MapUnit"/>
                <Option type="QString" name="joinstyle" value="round"/>
                <Option type="QString" name="capstyle" value="round"/>
              </Option>
            </layer>
          </symbol>
        </layer>

        <!-- 3. 진한 회색 (offset +12m) -->
        <layer class="GeometryGenerator" enabled="1" pass="4" locked="0">
          <Option type="Map">
            <Option type="QString" name="SymbolType" value="Line"/>
            <Option type="QString" name="geometryModifier" value="offset_curve($geometry, 12)"/>
          </Option>
          <symbol type="line" name="@0@4" alpha="1" clip_to_extent="1" force_rhr="0">
            <layer class="SimpleLine" enabled="1" pass="0" locked="0">
              <Option type="Map">
                <Option type="QString" name="line_color" value="102,102,102,255"/>
                <Option type="QString" name="line_style" value="solid"/>
                <Option type="QString" name="line_width" value="6"/>
                <Option type="QString" name="line_width_unit" value="MapUnit"/>
                <Option type="QString" name="joinstyle" value="round"/>
                <Option type="QString" name="capstyle" value="round"/>
              </Option>
            </layer>
          </symbol>
        </layer>

        <!-- 2. 연한 회색 (offset +6m) -->
        <layer class="GeometryGenerator" enabled="1" pass="5" locked="0">
          <Option type="Map">
            <Option type="QString" name="SymbolType" value="Line"/>
            <Option type="QString" name="geometryModifier" value="offset_curve($geometry, 6)"/>
          </Option>
          <symbol type="line" name="@0@5" alpha="1" clip_to_extent="1" force_rhr="0">
            <layer class="SimpleLine" enabled="1" pass="0" locked="0">
              <Option type="Map">
                <Option type="QString" name="line_color" value="170,170,170,255"/>
                <Option type="QString" name="line_style" value="solid"/>
                <Option type="QString" name="line_width" value="6"/>
                <Option type="QString" name="line_width_unit" value="MapUnit"/>
                <Option type="QString" name="joinstyle" value="round"/>
                <Option type="QString" name="capstyle" value="round"/>
              </Option>
            </layer>
          </symbol>
        </layer>

        <!-- 1. 기준선 - 검은색 (offset 0) -->
        <layer class="SimpleLine" enabled="1" pass="6" locked="0">
          <Option type="Map">
            <Option type="QString" name="line_color" value="0,0,0,255"/>
            <Option type="QString" name="line_style" value="solid"/>
            <Option type="QString" name="line_width" value="6"/>
            <Option type="QString" name="line_width_unit" value="MapUnit"/>
            <Option type="QString" name="joinstyle" value="round"/>
            <Option type="QString" name="capstyle" value="round"/>
          </Option>
        </layer>

      </symbol>
    </symbols>
  </renderer-v2>
</qgis>
