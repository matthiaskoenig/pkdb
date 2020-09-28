<template>
  <v-navigation-drawer
      v-model="drawer"
      :mini-variant.sync="mini"
      clipped
      permanent
      app
      right
      dark
      mini-variant-width="40"
      width="450"
  >
    <v-list-item @click.stop="mini = !mini" title="Hide details panel">
      <v-btn
          x-small
          icon
          v-if="!mini"
          @click.stop="mini = !mini"
      >
        <v-icon>{{ faIcon("right_arrow") }}</v-icon>
      </v-btn>

      <v-list-item-avatar v-if="mini" title="Show details panel">
        <v-icon>{{ faIcon('info') }}</v-icon>
      </v-list-item-avatar>

    </v-list-item>

    <!--<v-divider v-if="!mini"/>-->
    <div v-if="!mini">
      <v-list-item class="ma-0 pa-0">
        <info-node-detail v-if="show_type === 'info_node'" :data="detail_info"/>
        <search-help v-if="show_type === 'help'"/>
        <study-overview v-if="show_type === 'study'" :study="detail_info"/>
        <individual-detail v-if="show_type === 'individual'" :individual="detail_info"/>
        <group-detail v-if="show_type === 'group'" :group="detail_info"/>
        <intervention-detail v-if="show_type === 'intervention'" :intervention="detail_info"/>

      </v-list-item>
    </div>

  </v-navigation-drawer>
</template>

<script>


import {IconsMixin} from "../../icons";
import SearchHelp from "../search/SearchHelp";
import InfoNodeDetail from "../detail/InfoNodeDetail";
import StudyOverview from "../detail/StudyOverview";
import GroupDetail from "../detail/GroupDetail";
import IndividualDetail from "../detail/IndividualDetail";
import InterventionDetail from "../detail/InterventionDetail";

export default {
  name: 'DetailDrawer',
  components: {InterventionDetail, IndividualDetail, GroupDetail, SearchHelp, StudyOverview,InfoNodeDetail},
  mixins: [IconsMixin],
  data: () => ({
    drawer:true
  }),
  computed:{
    mini:  {
      get() {
        return !this.$store.state.display_detail
      },
      set(value) {
        this.$store.dispatch('updateAction', {
          key: "display_detail",
          value: !value,
        })
      }
    },
    detail_info: {
      get() {
        return this.$store.state.detail_info
      },
      set(value) {
        this.$store.dispatch('updateAction', {
          key: "detail_info",
          value: value,
        })
      }
    },
    show_type: {
      get() {
        return this.$store.state.show_type
      },
      set(value) {
        this.$store.dispatch('updateAction', {
          key: "show_type",
          value: value,
        })
      }
    }
  }
}
</script>

<style>
</style>